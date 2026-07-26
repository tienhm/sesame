# Development Guide

This guide is for developers who want to run, build, or contribute to Sesame from source including agent-based development. 🤖🤝🧑‍💻

---

## Prerequisites

- Windows 10 / 11
- Python 3.11+
- Git

---

## Setup

```powershell
# 1. Clone the repository
git clone <repo-url>
cd sesame

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

> **IMPORTANT:** Always activate `.venv` before running any Python command. See the **Virtual Environment** section below for details.

---

## Virtual Environment

### 🔴 Mandatory Rule

**You MUST activate `.venv` before running any Python command!**

---

### ✅ Correct Usage

#### PowerShell

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Then run Python commands
python -m py_compile main.py
pip install package-name
pyinstaller sesame.spec --noconfirm
```

#### Command Prompt (cmd)

```cmd
# Activate venv
.venv\Scripts\activate.bat

# Then run Python commands
python -m py_compile main.py
pip install package-name
```

#### Bash (Git Bash / WSL)

```bash
# Activate venv
source .venv/Scripts/activate

# Then run Python commands
python -m py_compile main.py
pip install package-name
```

---

### ❌ Wrong — Do Not Do This

```powershell
# ❌ WRONG — Running global Python
python main.py

# ❌ WRONG — Global pip
pip install package-name

# ❌ WRONG — Global PyInstaller (also rebuilds without bundled resources)
pyinstaller --onefile main.py
```

**Result**: `ModuleNotFoundError: No module named 'PySide6'` or similar errors

---

### 🎯 How to Tell Activation Succeeded

When `.venv` is activated, the command prompt shows:

```powershell
(.venv) PS D:\workspace\sesame>
```

Or:

```bash
(.venv) $ 
```

**If you don't see `(.venv)` → not activated!**

---

### 📋 Common Commands

#### Activate venv (must do first)

```powershell
.\.venv\Scripts\Activate.ps1
```

#### Deactivate venv (when done)

```powershell
deactivate
```

#### Run GUI

```powershell
python main.py
```

#### Run tests

```powershell
python -m pytest tests/
```

#### Compile check

```powershell
python -m py_compile main.py app\bubble.py app\dialogs\settings.py
```

#### Build executable

```powershell
pyinstaller sesame.spec --noconfirm
```

#### Install dependencies

```powershell
pip install -r requirements.txt
```

#### Add a new package

```powershell
pip install package-name
pip freeze > requirements.txt
```

---

### 🔍 Verify Venv

#### Check Python path

```powershell
python -c "import sys; print(sys.executable)"
```

**Correct**: `D:\workspace\sesame\.venv\Scripts\python.exe`  
**Wrong**: `C:\Users\...\AppData\Local\Programs\Python\...`

#### Check installed packages

```powershell
pip list
```

**Should show**: click, inquirer, keyring, cryptography, PySide6, etc.

#### Check Python version

```powershell
python --version
```

**Should be**: Python 3.11+

---

### 🚨 Forgot to Activate?

#### Symptoms

```
ModuleNotFoundError: No module named 'PySide6'
ModuleNotFoundError: No module named 'keyring'
```

#### Fix

1. **Activate venv**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Re-run the command**
   ```powershell
   python main.py
   ```

3. **Done!**

---

### 📝 Pre-Run Checklist

- [ ] Open PowerShell / cmd
- [ ] Navigate to `d:\workspace\sesame`
- [ ] Run `.\.venv\Scripts\Activate.ps1`
- [ ] Confirm the prompt shows `(.venv)`
- [ ] Run Python commands

---

### 🔄 Standard Workflow

```powershell
# 1. Open PowerShell
# 2. Navigate to the project folder
cd d:\workspace\sesame

# 3. Activate venv (REQUIRED)
.\.venv\Scripts\Activate.ps1

# 4. Confirm (.venv) appears in prompt
# (.venv) PS D:\workspace\sesame>

# 5. Run commands
python main.py
pyinstaller sesame.spec --noconfirm

# 6. Deactivate when done (optional)
deactivate
```

---

### 💡 Tips

#### Create an alias for quick activation

```powershell
# Add to your PowerShell profile
Set-Alias activate '.\.venv\Scripts\Activate.ps1'

# Then just type
activate
```

#### Create a batch file for activation

```batch
@echo off
cd /d D:\workspace\sesame
.venv\Scripts\activate.bat
cmd /k
```

Save as `sesame-dev.bat` and double-click to open a pre-activated terminal.

---

### ⚡ Summary

| Action | Command |
|--------|---------|
| **Activate venv** | `.\.venv\Scripts\Activate.ps1` |
| **Run GUI** | `python main.py` |
| **Build EXE** | `pyinstaller sesame.spec --noconfirm` |
| **Install package** | `pip install package-name` |
| **Deactivate** | `deactivate` |

**Always remember**: Activate venv before running any Python command!

---

**No activation = ModuleNotFoundError = wasted debugging time**

**Activate venv = everything works**

---

**Golden Rule**: 
```
🔑 .venv = Activate first, run later
```

---

## Run from source

```powershell
.\.venv\Scripts\Activate.ps1

# GUI
python main.py
```

---

## Project Structure

```
sesame/
├── main.py                  # Application entry point and controller
├── app/
│   ├── config.py            # User preferences and protected defaults
│   ├── bubble.py            # Floating always-on-top draggable button
│   ├── vault_panel.py       # Main panel: search, tag filter, entry list
│   ├── tray.py              # System tray icon and context menu
│   ├── dialogs/
│   │   ├── add_entry.py     # Add / Edit entry dialog
│   │   ├── export_import.py # Export / Import vault dialogs
│   │   ├── settings.py      # Settings dialog
│   │   ├── movement_confirm.py # Movement reminder confirmation dialog
│   │   └── categories.py    # Category management helper
│   ├── models/
│   │   ├── entry.py         # Entry dataclass
│   │   └── vault.py         # CRUD operations via Windows Credential Manager
│   └── utils/
│       ├── clipboard.py     # Copy to clipboard + auto-clear
│       ├── credential_store.py  # Direct win32cred access
│       ├── icons.py         # Font Awesome 6 icon loader
│       ├── lock_manager.py  # Master password lock per category
│       ├── movement_reminder.py # Movement reminder timer
│       ├── otp_import.py    # Parse otpauth:// and migration URIs
│       ├── startup.py       # Windows startup registry helper
│       ├── vault_io.py      # AES-256-GCM encryption for export
│       └── auto_login.py    # Keystroke injection for auto-login
├── resources/
│   ├── icon.png
│   ├── style.qss            # Dark theme stylesheet
│   ├── fa-solid-900.ttf     # Font Awesome icon font
│   ├── spin_up.png          # Spinbox up arrow
│   └── spin_down.png        # Spinbox down arrow
├── requirements.txt
├── sesame.spec              # PyInstaller build spec
└── README.md                # End-user documentation
```

---

## Architecture Overview

`SesameApp` (in `main.py`) wires together the main components:

1. **Vault** (`app/models/vault.py`) — stores entry metadata in `sesame_vault.json` and secrets/OTP in Windows Credential Manager.
2. **Bubble** (`app/bubble.py`) — floating always-on-top button that toggles the vault panel and shows clipboard countdown.
3. **VaultPanel** (`app/vault_panel.py`) — main expanded window with search, category/tag filters, and entry rows.
4. **TrayIcon** (`app/tray.py`) — system tray menu for show/hide, locate, settings, exit.
5. **SettingsDialog** (`app/dialogs/settings.py`) — settings for General, Categories, Security, Data.
6. **MovementReminder** (`app/utils/movement_reminder.py`) — idle timer and hibernate handling.
7. **AppConfig** (`app/config.py`) — JSON config in `%APPDATA%\Sesame\config.json`.

---

## Storage

| What | Where |
|---|---|
| Entry metadata | `%APPDATA%\Sesame\sesame_vault.json` — plain JSON, no secrets |
| Password + OTP secret | Windows Credential Manager — `SZM:<entry-id>`, blob = `{"p":"…","o":"…"}` |
| UI preferences / tunables | `%APPDATA%\Sesame\config.json` — no secrets |
| Transient UI coordinates (bubble position, background crop offset) | `%APPDATA%\Sesame\cache.json` — no secrets, updated automatically |

Windows DPAPI encrypts Credential Manager entries automatically.

---

## Security

### Reporting a vulnerability

Do **not** report security vulnerabilities through public GitHub issues. Use GitHub's private vulnerability reporting instead:

👉 **[Report a vulnerability](https://github.com/tienhm/sesame/security/advisories/new)**

Include as much detail as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within **72 hours**.

### In scope

- Secrets unintentionally written to disk, logs, or temp files
- Master password UI/logic bypass (e.g. a code path that skips the prompt)
- Clipboard secret not cleared after the 30-second countdown due to a bug
- Export file: incorrect use of AES-256-GCM (e.g. IV reuse, missing authentication tag check)
- Export file: PBKDF2 iteration count or salt handling bug that weakens the derived key

### Out of scope

- Theoretical breaks of AES-256-GCM or PBKDF2 as algorithms — these are handled by the upstream `cryptography` library
- Vulnerabilities requiring physical access to an already unlocked Windows session (Windows DPAPI is the trust boundary)
- Social engineering attacks
- Denial of service against the local application

---

## Build

Always build with the spec file so `resources/` are bundled:

```powershell
.\.venv\Scripts\Activate.ps1
pyinstaller sesame.spec --noconfirm
```

Output:

```text
dist/Sesame-*.exe
```

See [`BUILD_SUMMARY.md`](BUILD_SUMMARY.md) for full build and distribution details.

---

## Dependencies

| Package | Purpose |
|---|---|
| `PySide6` | Qt6 UI framework |
| `keyring` | Credential Manager abstraction (migration) |
| `pywin32` | Direct Windows Credential Manager access |
| `cryptography` | AES-256-GCM export encryption; PBKDF2 master password |
| `pyotp` | TOTP code generation |
| `pillow` | PNG conversion for PyInstaller (build only) |
| `pyinstaller` | Package to standalone `.exe` (build only) |

---

## Key Concepts

- **Tags** — comma-separated strings per entry; filtering uses AND logic.
- **Master password** — one shared PBKDF2-HMAC-SHA256 hash protects selected categories; plaintext is never stored.
- **Export/Import** — vault JSON encrypted with AES-256-GCM using a PBKDF2-derived key.
- **Protected config** — UI timing/sizing constants live in `_PROTECTED_CONFIG` and are read one-way from `config.json`; they are never overwritten by the app.

---

## Useful Commands

| Action | Command |
|---|---|
| Compile check | `python -m py_compile main.py` |
| Run GUI | `python main.py` |
| Build EXE | `pyinstaller sesame.spec --noconfirm` |
| Update deps | `pip install -r requirements.txt` |

---

## Build Summary

### ✅ Build Complete

Executable file created successfully using PyInstaller.

### ⚠️ Fixed in v1.4: Missing resources bundle

The initial build command (`pyinstaller --onefile --windowed --name Sesame --icon resources\icon.png main.py`)
did **not** bundle the `resources/` folder (Font Awesome font, `style.qss`, `icon.png`).
This caused, when running the packaged `.exe`:
- Font Awesome icons not rendering (bubble, tray, buttons) → boxes/fallback glyphs
- Bubble showing default Qt button styling (hard to see) instead of the round dark style
- No transparent panel background (missing `style.qss`)
- Tray icon key glyph missing

**Fix**: `sesame.spec` now includes `datas=[('resources', 'resources')]`. Always build via:

```powershell
pyinstaller sesame.spec --noconfirm
```

Do **not** rebuild with the raw `--onefile` command line above — it regenerates a spec without the `datas` entry.

#### Output

```
📦 dist/Sesame-v1.4.exe
```

**Size**: ~150-200 MB (includes Python runtime + all dependencies)  
**Type**: Standalone Windows executable (no Python installation required)  
**Architecture**: 64-bit Intel  
**Filename**: `Sesame-v1.4.exe` (versioned from `main.py`)

---

### Build Details

#### Command Used

```powershell
.venv\Scripts\python.exe -m PyInstaller sesame.spec --noconfirm --clean
```

or, after activating the venv:

```powershell
pyinstaller sesame.spec --noconfirm
```

#### Build Options

| Option | Value | Purpose |
|--------|-------|---------|
| `--onefile` | ✓ | Single executable (not folder) |
| `--windowed` | ✓ | No console window |
| `--name Sesame-v1.4` | ✓ | Executable name (read from `main.py`)
| `--icon` | resources/icon.png | Window icon |

#### Build Artifacts

```
dist/
├── Sesame-v1.4.exe     ← Main executable
└── (no other files needed)

build/
├── sesame/             ← Build intermediate files
└── ...

sesame.spec            ← Build configuration (can be reused)
```

---

### Distribution

#### Option 1: Direct Distribution (Simplest)

Just distribute `dist/Sesame-v1.4.exe`:

```bash
# User downloads Sesame-v1.4.exe and runs it
Sesame-v1.4.exe
```

**Pros**:
- Single file
- No installation needed
- Works on any Windows 10/11 machine

**Cons**:
- Large file (~150-200 MB)
- No uninstall mechanism

#### Option 2: Create Installer (NSIS)

Use NSIS to create `Sesame-Setup.exe`:

```nsis
; sesame-installer.nsi
Name "Sesame v1.4"
OutFile "Sesame-Setup.exe"
InstallDir "$PROGRAMFILES\Sesame"

Section "Install"
  SetOutPath "$INSTDIR"
  File "dist\Sesame-v1.4.exe"
  CreateDirectory "$SMPROGRAMS\Sesame"
  CreateShortCut "$SMPROGRAMS\Sesame\Sesame.lnk" "$INSTDIR\Sesame-v1.4.exe"
  CreateShortCut "$DESKTOP\Sesame.lnk" "$INSTDIR\Sesame-v1.4.exe"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\Sesame-v1.4.exe"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\Sesame\Sesame.lnk"
  RMDir "$SMPROGRAMS\Sesame"
  Delete "$DESKTOP\Sesame.lnk"
SectionEnd
```

**Pros**:
- Professional installer
- Start menu shortcuts
- Uninstall support
- Smaller download (compressed)

**Cons**:
- Requires NSIS tool
- Extra build step

#### Option 3: ZIP Archive (Portable)

```bash
# Create portable ZIP
Compress-Archive -Path dist\Sesame-v1.4.exe -DestinationPath Sesame-v1.4-portable.zip
```

**Pros**:
- Portable (no installation)
- Easy to distribute
- Works on any Windows

**Cons**:
- Large file
- No shortcuts created

---

### System Requirements

#### Minimum

- **OS**: Windows 10 or later
- **Architecture**: 64-bit
- **RAM**: 256 MB
- **Disk**: 200 MB free space

#### Recommended

- **OS**: Windows 11
- **RAM**: 512 MB+
- **Disk**: 300 MB free space

---

### What's Included

The executable includes:

✅ **Core Features**
- Floating bubble UI
- Vault panel with search/filter
- Add/Edit/Delete entries
- Password generator
- Master password protection
- Category management
- Background image support

✅ **Advanced Features**
- Export/Import encrypted vaults (AES-256-GCM)
- OTP (2FA) support
- Movement reminder with blinking bubble
- Hibernate/resume detection
- Windows startup integration
- System tray icon

✅ **Security**
- Windows Credential Manager (DPAPI) storage
- Clipboard exclusion from Win+V history
- 30-second auto-clear for passwords
- PBKDF2-HMAC-SHA256 master password (600k iterations)

✅ **UI**
- Modern dark theme
- Responsive layout
- Drag-to-reorder entries
- Real-time search
- Tag-based filtering (AND logic)

---

### Testing

#### Quick Test

1. Run `Sesame-v1.4.exe`
2. Bubble should appear in bottom-right corner
3. Click bubble → panel opens
4. Add a test entry
5. Copy password → countdown appears
6. Settings → General → Movement reminder (set to 1 min)
7. Wait 1 min → bubble blinks orange
8. Click bubble → dialog appears
9. Close app → settings saved

#### Verification Checklist

- [ ] Bubble appears on startup
- [ ] Click bubble → panel opens
- [ ] Add entry → saved in vault
- [ ] Copy password → clipboard works
- [ ] 30-second countdown → clipboard clears
- [ ] Settings → changes persist
- [ ] Movement reminder → blinking works
- [ ] Hibernate → timer resets
- [ ] Export → creates .sesame file
- [ ] Import → restores entries
- [ ] Master password → protects categories
- [ ] Tray icon → context menu works
- [ ] Exit → no errors

---

### Troubleshooting

#### "Windows protected your PC" Message

Windows SmartScreen may block the executable. Click "More info" → "Run anyway".

**Solution**: Sign the executable with a code signing certificate (optional).

#### Slow Startup

First run may be slow (Windows caching). Subsequent runs are faster.

#### Missing Icon

If icon doesn't appear, check `resources/icon.png` exists.

---

### Rebuild Instructions

To rebuild after code changes:

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Rebuild (always use the spec file — bundles resources/ correctly)
pyinstaller sesame.spec --noconfirm

# Test
.\dist\Sesame-v1.4.exe
```

---

### Version Info

| Component | Version |
|-----------|---------|
| Sesame | 1.4 |
| Python | 3.11 |
| PySide6 | 6.6+ |
| PyInstaller | 6.0+ |

---

### File Locations

```
d:\workspace\sesame\
├── dist/
│   └── Sesame-v1.4.exe         ← MAIN EXECUTABLE
├── build/                       ← Build artifacts (can delete)
├── Sesame.spec                  ← Build config
├── main.py                      ← Entry point
├── app/                         ← Application code
├── resources/                   ← Icons, styles
└── requirements.txt             ← Dependencies
```

---

### Next Steps

1. **Test thoroughly** on different Windows versions
2. **Create installer** (NSIS) for professional distribution
3. **Sign executable** with code signing certificate
4. **Create release notes** documenting v1.4 features
5. **Upload to GitHub Releases** for distribution

---

### Summary

✅ **Sesame v1.4 is now packaged as a standalone Windows executable**

- Single file: `dist/Sesame-v1.4.exe`
- No Python installation required
- All features included (GUI, vault, encryption, OTP, movement reminder)
- Ready for distribution

**To use**: Simply run `Sesame-v1.4.exe` on any Windows 10/11 machine.

---

**Build Date**: July 26, 2026  
**Build Tool**: PyInstaller 6.21.0  
**Status**: ✅ Ready for Distribution

---

## More Documentation

- [`README.md`](README.md) — end-user documentation
- [`CHANGELOG.md`](CHANGELOG.md) — version history
- [`RELEASE_NOTES_v1.4.md`](RELEASE_NOTES_v1.4.md) — latest release notes
