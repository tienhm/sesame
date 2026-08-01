"""Local HTTP server for the Sesame Pass browser extension.

Binds 127.0.0.1 only, on a background daemon thread. Pairing is a one-time
step: the user copies base64("<uuid>:<port>") from Settings into the
extension popup; the extension then sends that same base64 string back as
the `Authorization: Bearer <code>` header on every authenticated request.

`/ping` is the only endpoint that does not require auth — it doubles as a
liveness health-check (content script, before offering to autofill) and as
the extension's heartbeat (background script, every ~15s, reports which
browser is calling so Settings can show it as paired).

The HTTP handler runs on a background thread and must never touch Qt widgets
directly — it only updates plain attributes here and emits Qt signals via
`ExtensionServer.bridge`, which Qt marshals across threads safely.
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
import uuid as _uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QObject, Signal

from app.config import AppConfig
from app.models.vault import Vault
from app.utils import credential_store
from app.utils.lock_manager import LockManager

logger = logging.getLogger(__name__)

_FIRST_PORT = 37821
_MAX_PORT_SCAN = 50
# Chrome's MV3 chrome.alarms API clamps periods below 1 minute for published
# (non-dev-mode) extensions, so background.js's heartbeat realistically fires
# every ~60s rather than the originally-planned 15s. Timeout is set to 1.5x
# that worst case so "Connected" doesn't flicker off between alarm ticks.
_HEARTBEAT_TIMEOUT_S = 90


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


class ExtensionBridge(QObject):
    """Thread-safe signal bridge — emitted from the HTTP handler thread,
    delivered on the Qt main thread via a queued connection."""

    heartbeat_received = Signal(str)   # browser name, e.g. "chrome"
    request_received = Signal()        # any request — used for a liveness dot


class ExtensionServer:
    """Owns the background HTTP server plus the pairing/auth state."""

    def __init__(self, config: AppConfig, vault: Vault, lock_mgr: LockManager) -> None:
        self._config = config
        self._vault = vault
        self._lock_mgr = lock_mgr
        self.bridge = ExtensionBridge()

        self._uuid: str = ""
        self.port: int = 0
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._last_ping: dict[str, float] = {}   # browser -> monotonic timestamp

        self._start()

    # ------------------------------------------------------------------
    # Public — pairing
    # ------------------------------------------------------------------

    @property
    def pairing_code(self) -> str:
        """base64("<uuid>:<port>") — shown once in Settings for the user to
        paste into the extension popup."""
        if not self.port:
            return ""
        raw = f"{self._uuid}:{self.port}"
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")

    def regenerate(self) -> None:
        """Revoke the current pairing and bind a fresh key (and, if needed,
        a fresh port). Existing extension installs get 401 until re-paired."""
        self.shutdown()
        credential_store.delete_extension_secret()
        self._last_ping.clear()
        for browser in list(self._config.get("_extension_paired_browsers", []) or []):
            self._config.set(f"extension_paired_{browser}", False)
        self._start(force_new_uuid=True)

    def shutdown(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    # ------------------------------------------------------------------
    # Public — connection status (polled by Settings UI)
    # ------------------------------------------------------------------

    def is_connected(self, browser: str) -> bool:
        last = self._last_ping.get(browser)
        return last is not None and (time.monotonic() - last) <= _HEARTBEAT_TIMEOUT_S

    # ------------------------------------------------------------------
    # Startup / lifecycle
    # ------------------------------------------------------------------

    def _start(self, force_new_uuid: bool = False) -> None:
        stored = "" if force_new_uuid else credential_store.get_extension_secret()
        stored_uuid, stored_port = "", 0
        if stored and ":" in stored:
            stored_uuid, _, port_str = stored.rpartition(":")
            try:
                stored_port = int(port_str)
            except ValueError:
                stored_port = 0

        self._uuid = stored_uuid or str(_uuid.uuid4())

        handler_cls = _make_handler(self)
        bound = False
        # Prefer the previously-bound port first — the extension already
        # decoded and stored it; silently switching ports breaks pairing.
        candidates = ([stored_port] if stored_port else []) + [
            _FIRST_PORT + i for i in range(_MAX_PORT_SCAN + 1)
        ]
        for try_port in candidates:
            try:
                self._httpd = ThreadingHTTPServer(("127.0.0.1", try_port), handler_cls)
            except OSError:
                continue
            self.port = try_port
            bound = True
            break

        if not bound:
            logger.error("ExtensionServer: could not bind any port (tried %d candidates)",
                         len(candidates))
            return

        credential_store.set_extension_secret(f"{self._uuid}:{self.port}")

        self._thread = threading.Thread(
            target=self._httpd.serve_forever, daemon=True, name="ExtensionServer"
        )
        self._thread.start()
        logger.info("ExtensionServer listening on 127.0.0.1:%d", self.port)

    # ------------------------------------------------------------------
    # Auth (called from the handler thread)
    # ------------------------------------------------------------------

    def check_auth(self, authorization_header: str) -> bool:
        if not authorization_header.startswith("Bearer "):
            return False
        token = authorization_header[len("Bearer "):].strip()
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except Exception:
            return False
        return bool(self.port) and decoded == f"{self._uuid}:{self.port}"

    # ------------------------------------------------------------------
    # Heartbeat (called from the handler thread)
    # ------------------------------------------------------------------

    def record_ping(self, browser: str = "") -> None:
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

    # ------------------------------------------------------------------
    # Data access (called from the handler thread)
    # ------------------------------------------------------------------

    def entries_for_domain(self, domain: str) -> list[dict]:
        return [
            {"id": e.id, "name": e.name, "has_username": bool(e.username), "has_otp": e.has_otp}
            for e in self._vault.entries
            if e.url and _domain_matches(e.url, domain)
        ]

    def reveal(self, entry_id: str, field: str) -> tuple[int, dict]:
        entry = next((e for e in self._vault.entries if e.id == entry_id), None)
        if entry is None:
            return 404, {"error": "not_found"}
        if self._lock_mgr.is_locked(entry.category):
            return 423, {"error": "locked"}
        if field == "username":
            return 200, {"value": entry.username}
        if field == "password":
            return 200, {"value": self._vault.get_secret(entry_id)}
        return 400, {"error": "invalid_field"}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

def _make_handler(owner: ExtensionServer):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            pass  # silence default stderr access log

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            return owner.check_auth(self.headers.get("Authorization", ""))

        def _read_json_body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                return json.loads(raw.decode("utf-8")) if raw else {}
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}

        def do_OPTIONS(self) -> None:  # noqa: N802 (stdlib naming convention)
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/ping":
                owner.record_ping()
                self._send_json(200, {"ok": True})
                return
            if parsed.path == "/entries":
                if not self._authorized():
                    self._send_json(401, {"error": "unauthorized"})
                    return
                domain = parse_qs(parsed.query).get("domain", [""])[0]
                self._send_json(200, {"entries": owner.entries_for_domain(domain)})
                return
            self._send_json(404, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            body = self._read_json_body()

            if parsed.path == "/ping":
                owner.record_ping(str(body.get("browser", "")))
                self._send_json(200, {"ok": True})
                return

            if parsed.path == "/reveal":
                if not self._authorized():
                    self._send_json(401, {"error": "unauthorized"})
                    return
                status, payload = owner.reveal(
                    str(body.get("entry_id", "")), str(body.get("field", ""))
                )
                self._send_json(status, payload)
                return

            self._send_json(404, {"error": "not_found"})

    return _Handler
