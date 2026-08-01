# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Sesame Pass native-messaging host — a separate,
# minimal executable from the main Sesame GUI app (no PySide6/Qt/vault code).
# Chrome/Edge spawn this directly per native-messaging session; see
# native_host.py and app/utils/native_host_registration.py for how it gets
# registered as `com.sesame.pass`.
#
# Build: pyinstaller native_host.spec
#
# Name is deliberately NOT version-suffixed (unlike Sesame-vX.Y.exe) — the
# registry/manifest path this exe is registered under should stay stable
# across version bumps.

import os

block_cipher = None

a = Analysis(
    ["native_host.py"],
    pathex=[os.path.abspath(".")],
    binaries=[],
    datas=[],
    hiddenimports=[
        "win32timezone",  # pywin32 freeze gotcha, needed even though not imported directly
        "win32file",
        "win32pipe",
        "pywintypes",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "cryptography", "pyotp", "PIL", "keyring", "inquirer"],
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
    name="sesame_native_host",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no console window — Chrome talks to it via pipes only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=False,
    uac_uiaccess=False,
)
