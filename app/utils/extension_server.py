"""Named-pipe bridge for the Sesame Pass browser extension (Native Messaging
architecture — replaces the old HTTP-loopback server).

The browser never talks to this process directly anymore. Chrome/Edge spawn
a short-lived native-messaging host process (`native_host.py`, built as its
own exe — see native_host.spec) per request, which is meant to be the only
thing that ever connects to this pipe, after the browser has already
verified the extension's ID against `allowed_origins` in the registered host
manifest (see `app/utils/native_host_registration.py`). That check only
constrains which *extension* Chrome will launch the native host for — it
says nothing about who else on the machine can open the pipe directly.
`CreateNamedPipe` defaults to a broad DACL when given no explicit security
descriptor, so without locking it down, any other process already running
as the same Windows user (not just the native host) could connect straight
to this pipe and issue `entries`/`reveal` requests, skipping the browser,
the extension-ID check, and the native host entirely. `_pipe_security_attributes()`
below closes that gap by restricting the pipe's DACL to the current user
(+ SYSTEM) — no bearer token, no port number, nothing to copy/paste into
the extension popup, but also no longer openable by an arbitrary co-resident
process.

Runs a named-pipe server on a background thread, accepting one client
connection at a time and handing each off to its own handler thread so a
slow/stuck client can't block new connections — Chrome may spawn several
native-host processes concurrently (one per tab that's actively autofilling).

Windows-only (named pipes are a Windows concept, and so is this whole
feature) — `_start()` is a no-op on other platforms.
"""

from __future__ import annotations

import logging
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal

from app.config import AppConfig
from app.models.vault import Vault
from app.utils import native_messaging
from app.utils.lock_manager import LockManager

logger = logging.getLogger(__name__)

# Chrome's MV3 chrome.alarms API clamps periods below 1 minute for published
# (non-dev-mode) extensions, so background.js's heartbeat realistically fires
# every ~60s rather than the originally-planned 15s. Timeout is set to 1.5x
# that worst case so "Connected" doesn't flicker off between alarm ticks.
_HEARTBEAT_TIMEOUT_S = 90
_PIPE_BUFFER_SIZE = 65536


def _normalize_host(url: str) -> str:
    """Strip protocol/path/port and a leading 'www.' for domain comparisons."""
    if not url:
        return ""
    u = url.lower().strip()
    for prefix in ("https://", "http://"):
        if u.startswith(prefix):
            u = u[len(prefix):]
            break
    u = u.split("/", 1)[0]
    u = u.split(":", 1)[0]
    if u.startswith("www."):
        u = u[4:]
    return u


def _domain_matches(entry_url: str, requested_domain: str) -> bool:
    entry_host = _normalize_host(entry_url)
    req_host = _normalize_host(requested_domain)
    return bool(entry_host) and entry_host == req_host


def _pipe_security_attributes():
    """SECURITY_ATTRIBUTES restricting the named pipe's DACL to the current
    Windows user plus SYSTEM — CreateNamedPipe's default (no explicit
    descriptor) is broad enough that any other locally-running process under
    this same account could otherwise open the pipe directly. Built once per
    server start and reused for every pipe instance; the DACL doesn't change
    between connections."""
    import pywintypes
    import win32api
    import win32security

    token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
    user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
    sid_str = win32security.ConvertSidToStringSid(user_sid)
    # D: DACL, (A;;GA;;;<sid>) = Allow Generic-All to the given SID. No ACE
    # for anyone else means everyone else is implicitly denied.
    sddl = f"D:(A;;GA;;;{sid_str})(A;;GA;;;SY)"
    security_descriptor, _ = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        sddl, win32security.SDDL_REVISION_1
    )
    sa = pywintypes.SECURITY_ATTRIBUTES()
    sa.SECURITY_DESCRIPTOR = security_descriptor
    return sa


class ExtensionBridge(QObject):
    """Thread-safe signal bridge — emitted from a pipe-client handler thread,
    delivered on the Qt main thread via a queued connection."""

    heartbeat_received = Signal(str)   # browser name, e.g. "chrome"
    request_received = Signal()        # any request — used for a liveness dot


class ExtensionServer:
    """Owns the background named-pipe server plus heartbeat bookkeeping."""

    def __init__(self, config: AppConfig, vault: Vault, lock_mgr: LockManager) -> None:
        self._config = config
        self._vault = vault
        self._lock_mgr = lock_mgr
        self.bridge = ExtensionBridge()

        self._stop = False
        self._thread: threading.Thread | None = None
        self._last_ping: dict[str, float] = {}   # browser -> monotonic timestamp

        self._start()

    # ------------------------------------------------------------------
    # Public — connection status (polled by Settings UI)
    # ------------------------------------------------------------------

    def is_connected(self, browser: str) -> bool:
        last = self._last_ping.get(browser)
        return last is not None and (time.monotonic() - last) <= _HEARTBEAT_TIMEOUT_S

    # ------------------------------------------------------------------
    # Startup / lifecycle
    # ------------------------------------------------------------------

    def _start(self) -> None:
        if sys.platform != "win32":
            logger.info("ExtensionServer: non-Windows platform — native-messaging bridge disabled")
            return
        self._stop = False
        self._thread = threading.Thread(target=self._accept_loop, daemon=True, name="ExtensionServer")
        self._thread.start()
        logger.info("ExtensionServer listening on pipe %s", native_messaging.PIPE_NAME)

    def shutdown(self) -> None:
        if self._thread is None:
            return
        self._stop = True
        self._unblock_accept_loop()
        self._thread.join(timeout=2)
        self._thread = None

    def _unblock_accept_loop(self) -> None:
        """The accept loop blocks in ConnectNamedPipe() — connecting to our
        own pipe as a throwaway client is the standard way to unstick it so
        shutdown() doesn't have to wait for a real client."""
        import pywintypes
        import win32file
        try:
            handle = win32file.CreateFile(
                native_messaging.PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None,
            )
            win32file.CloseHandle(handle)
        except pywintypes.error:
            pass

    def _accept_loop(self) -> None:
        import pywintypes
        import win32file
        import win32pipe

        try:
            pipe_sa = _pipe_security_attributes()
        except Exception:
            # win32security unavailable — pipe created with default DACL.
            # Any same-user process can connect; log at WARNING so this is
            # visible in production. Root fix: win32security in hiddenimports.
            logger.warning(
                "ExtensionServer: pipe security descriptor failed — "
                "falling back to default DACL (same-user processes can connect). "
                "Ensure win32security is available.",
                exc_info=True,
            )
            pipe_sa = None

        while not self._stop:
            try:
                handle = win32pipe.CreateNamedPipe(
                    native_messaging.PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    _PIPE_BUFFER_SIZE, _PIPE_BUFFER_SIZE, 0, pipe_sa,
                )
            except pywintypes.error:
                logger.exception("ExtensionServer: CreateNamedPipe failed")
                return

            try:
                win32pipe.ConnectNamedPipe(handle, None)
            except pywintypes.error:
                win32file.CloseHandle(handle)
                continue

            if self._stop:
                win32file.CloseHandle(handle)
                break

            threading.Thread(target=self._handle_client, args=(handle,), daemon=True).start()

    def _handle_client(self, handle) -> None:
        import pywintypes
        import win32file

        def _read(n: int) -> bytes:
            try:
                _err, data = win32file.ReadFile(handle, n)
            except pywintypes.error:
                return b""
            return data

        try:
            while True:
                try:
                    message = native_messaging.read_message(_read)
                except native_messaging.FramingError:
                    break
                if message is None:
                    break
                response = self._dispatch(message)
                try:
                    win32file.WriteFile(handle, native_messaging.pack_message(response))
                except pywintypes.error:
                    break
        finally:
            try:
                win32file.CloseHandle(handle)
            except pywintypes.error:
                pass

    # ------------------------------------------------------------------
    # Request handling (called from a pipe-client handler thread)
    # ------------------------------------------------------------------

    def _dispatch(self, message: dict) -> dict:
        msg_type = message.get("type")
        if msg_type == "ping":
            self._record_ping(str(message.get("browser", "")))
            return {"ok": True}
        if msg_type == "entries":
            self.bridge.request_received.emit()
            return {"entries": self._entries_for_domain(str(message.get("domain", "")))}
        if msg_type == "reveal":
            self.bridge.request_received.emit()
            return self._reveal(
                str(message.get("entry_id", "")),
                str(message.get("field", "")),
                str(message.get("domain", "")),
            )
        return {"error": "invalid_request"}

    def _record_ping(self, browser: str) -> None:
        browser = browser.lower().strip()
        if browser:
            self._last_ping[browser] = time.monotonic()
            if not self._config.get(f"extension_paired_{browser}", False):
                self._config.set(f"extension_paired_{browser}", True)
                paired = set(self._config.get("_extension_paired_browsers", []) or [])
                paired.add(browser)
                self._config.set("_extension_paired_browsers", sorted(paired))
            self.bridge.heartbeat_received.emit(browser)
        self.bridge.request_received.emit()

    def _entries_for_domain(self, domain: str) -> list[dict]:
        return [
            {"id": e.id, "name": e.name, "username": e.username or "", "has_otp": e.has_otp}
            for e in self._vault.entries
            if e.url and _domain_matches(e.url, domain)
        ]

    def _reveal(self, entry_id: str, field: str, domain: str = "") -> dict:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if entry is None:
            return {"error": "not_found"}
        # Domain check: the requested entry must belong to the domain the
        # extension is currently on. Prevents cross-domain enumeration via
        # direct pipe access (sequential entry IDs make brute-force trivial).
        if domain and not _domain_matches(entry.url, domain):
            return {"error": "not_found"}
        if self._lock_mgr.is_locked(entry.category):
            return {"error": "locked"}
        if field == "username":
            return {"value": entry.username}
        if field == "password":
            return {"value": self._vault.get_secret(entry_id)}
        return {"error": "invalid_field"}
