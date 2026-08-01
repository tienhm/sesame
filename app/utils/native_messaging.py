"""Shared plumbing for the Sesame Pass native-messaging bridge.

Framing helpers here match Chrome's own native-messaging stdio protocol (a
4-byte little-endian length prefix + UTF-8 JSON body) so `native_host.py` can
reuse the exact same helpers on both sides of the relay: reading/writing
Chrome's stdin/stdout framing, and reading/writing the same shape of message
over the local named pipe to the Sesame GUI process (`extension_server.py`).

Deliberately has ZERO PySide6/Qt import — `native_host.py` is built as its own
tiny executable (see native_host.spec) that must stay far away from Qt/vault
code, so anything imported here ends up in that process too.
"""

from __future__ import annotations

import json
import struct
from typing import Callable

# Named pipe the Sesame GUI process listens on and native_host.py connects to.
# Windows-only concept — this whole bridge is a no-op off Windows (see
# ExtensionServer._start).
PIPE_NAME = r"\\.\pipe\SesamePassExt"


class FramingError(Exception):
    """Raised when a length-prefixed message stream ends mid-frame."""


def pack_message(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return struct.pack("<I", len(body)) + body


def _read_exact(read_fn: Callable[[int], bytes], n: int) -> bytes:
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = read_fn(remaining)
        if not chunk:
            raise FramingError("stream closed mid-message")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_message(read_fn: Callable[[int], bytes]) -> dict | None:
    """Read one framed message using `read_fn(n) -> bytes` (file.read-like).

    Returns None on a clean EOF before any bytes of the length prefix were
    read — the normal "other side closed the connection" case. Raises
    FramingError if the stream dies partway through a frame.
    """
    header = read_fn(4)
    if not header:
        return None
    if len(header) < 4:
        header += _read_exact(read_fn, 4 - len(header))
    (length,) = struct.unpack("<I", header)
    body = _read_exact(read_fn, length) if length else b""
    return json.loads(body.decode("utf-8")) if body else {}
