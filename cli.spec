# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Sesame CLI
Build with: pyinstaller cli.spec
"""

block_cipher = None

a = Analysis(
    ['cli.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'keyring',
        'keyring.backends',
        'keyring.backends.Windows',
        'keyring.backends.chainer',
        'keyring.util',
        'keyring.util.platform_',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.kdf',
        'click',
        'inquirer',
        'inquirer.themes',
        'inquirer.render',
        'inquirer.render.console',
        'blessed',
        'readchar',
        'wcwidth',
        'jinxed',
        'runs',
        'xmod',
        'ansicon',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    name='sesame',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
