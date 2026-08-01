# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Sesame
# Build: pyinstaller sesame.spec

import os
import re

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# Read version from main.py
_version = "0.0"
with open("main.py", encoding="utf-8") as _f:
    _m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', _f.read(), re.MULTILINE)
    if _m:
        _version = _m.group(1)

# Build a 4-part version tuple and a dotted version string for the resource.
_version_parts = [int(p) for p in _version.split(".")]
while len(_version_parts) < 4:
    _version_parts.append(0)
_version_tuple = tuple(_version_parts)
_version_str = ".".join(str(p) for p in _version_parts)

_vi = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_version_tuple,
        prodvers=_version_tuple,
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        StringFileInfo(
            [
                StringTable(
                    "040904b0",
                    [
                        StringStruct("CompanyName", "TienHM"),
                        StringStruct("FileDescription", "Sesame Password Manager"),
                        StringStruct("FileVersion", _version_str),
                        StringStruct("InternalName", "Sesame"),
                        StringStruct(
                            "LegalCopyright",
                            "Copyright \u00a9 2026 TienHM. All rights reserved.",
                        ),
                        StringStruct("OriginalFilename", f"Sesame-v{_version}.exe"),
                        StringStruct("ProductName", "Sesame"),
                        StringStruct("ProductVersion", _version_str),
                    ],
                )
            ]
        ),
    ],
)

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[os.path.abspath(".")],
    binaries=[
        ("dist/szm_door.exe", "."),
    ],
    datas=[
        ("resources/style.qss", "resources"),
        ("resources/icon.png", "resources"),
        ("resources/fa-solid-900.ttf", "resources"),
        ("resources/spin_up.png", "resources"),
        ("resources/spin_down.png", "resources"),
        ("resources/check.svg", "resources"),
    ],
    hiddenimports=[
        "keyring.backends.Windows",
        "keyring.backends.fail",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "cryptography.hazmat.primitives.ciphers.aead",
        "cryptography.hazmat.backends.openssl",
        "PySide6.QtNetwork",
        "win32timezone",  # pywin32 freeze gotcha, needed even though not imported directly
        "win32cred",
        "pywintypes",
        "pyotp",           # imported dynamically at call-time in vault_panel.py
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f"Sesame-v{_version}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="resources/icon.png",
    version=_vi,
    uac_admin=False,        # no admin rights
    uac_uiaccess=False,
)
