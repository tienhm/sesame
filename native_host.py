"""Sesame Pass native-messaging host — the process Chrome/Edge actually spawn.

This is a separate, minimal executable (see native_host.spec) from the main
Sesame GUI app — no PySide6/Qt, no vault code. Chrome/Edge invoke it directly
per native-messaging session (one process per `chrome.runtime.connectNative()`
call from extension/background.js) and talk to it over stdin/stdout using
Chrome's own framing: a 4-byte little-endian length prefix + UTF-8 JSON body.

This process has no idea what a vault is. It only relays each framed message
byte-for-byte to the Sesame GUI process (which does hold the unlocked vault)
over a local named pipe, and relays the framed response back. If the GUI
process isn't running (pipe missing), it answers `{"error": "not_running"}`
directly so the extension never hangs waiting for a Sesame instance that
isn't there.
"""

from __future__ import annotations

import os
import sys

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils import native_messaging  # noqa: E402

_CONNECT_TIMEOUT_MS = 2000


_stdin_buf = None
_stdout_buf = None


def _stdin_read(n: int) -> bytes:
    return _stdin_buf.read(n)


def _stdout_write(data: bytes) -> None:
    _stdout_buf.write(data)
    _stdout_buf.flush()


def _set_binary_mode() -> None:
    global _stdin_buf, _stdout_buf
    if sys.platform != "win32":
        # Non-Windows: use sys.stdin/stdout directly (dev/testing only).
        _stdin_buf  = sys.stdin.buffer
        _stdout_buf = sys.stdout.buffer
        return
    import io
    import msvcrt

    if sys.stdin is None:
        # Frozen as windowed app (console=False) — PyInstaller leaves
        # sys.stdin/stdout as None. Chrome still passes the pipe via
        # handle inheritance; open them directly from Win32 STD handles.
        import win32api
        STD_INPUT_HANDLE, STD_OUTPUT_HANDLE = -10, -11
        h_in  = win32api.GetStdHandle(STD_INPUT_HANDLE)
        h_out = win32api.GetStdHandle(STD_OUTPUT_HANDLE)
        if h_in is None or h_out is None or int(h_in) in (0, -1) or int(h_out) in (0, -1):
            # Not spawned by Chrome — no valid stdio handles.
            sys.exit(1)
        fd_in  = msvcrt.open_osfhandle(int(h_in),  os.O_RDONLY | os.O_BINARY)
        fd_out = msvcrt.open_osfhandle(int(h_out), os.O_WRONLY | os.O_BINARY)
        _stdin_buf  = io.open(fd_in,  "rb", buffering=0)
        _stdout_buf = io.open(fd_out, "wb", buffering=0)
    else:
        msvcrt.setmode(sys.stdin.fileno(),  os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        _stdin_buf  = sys.stdin.buffer
        _stdout_buf = sys.stdout.buffer


def _forward_to_pipe(message: dict) -> dict:
    import pywintypes
    import win32file
    import win32pipe

    try:
        win32pipe.WaitNamedPipe(native_messaging.PIPE_NAME, _CONNECT_TIMEOUT_MS)
        handle = win32file.CreateFile(
            native_messaging.PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0, None, win32file.OPEN_EXISTING, 0, None,
        )
    except pywintypes.error:
        return {"error": "not_running"}

    try:
        win32file.WriteFile(handle, native_messaging.pack_message(message))

        def _read(n: int) -> bytes:
            try:
                _err, data = win32file.ReadFile(handle, n)
            except pywintypes.error:
                return b""
            return data

        response = native_messaging.read_message(_read)
        return response if response is not None else {"error": "not_running"}
    except native_messaging.FramingError:
        return {"error": "not_running"}
    finally:
        win32file.CloseHandle(handle)


def main() -> None:
    _set_binary_mode()
    while True:
        try:
            message = native_messaging.read_message(_stdin_read)
        except native_messaging.FramingError:
            break
        if message is None:
            break  # Chrome closed stdin — extension disconnected the port.
        try:
            response = _forward_to_pipe(message)
        except Exception:
            response = {"error": "not_running"}
        _stdout_write(native_messaging.pack_message(response))


if __name__ == "__main__":
    main()
