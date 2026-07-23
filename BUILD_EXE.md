# Build Sesame CLI as Standalone EXE

## Simple Method: Bundle with venv

Instead of using PyInstaller (which has complex dependency issues), we'll create a standalone package with the venv included.

### Step 1: Create Distribution Folder

```bash
# Create dist folder
mkdir dist\sesame-cli
```

### Step 2: Copy Files

```bash
# Copy CLI files
copy cli.py dist\sesame-cli\
copy app dist\sesame-cli\app /s
copy .venv dist\sesame-cli\.venv /s

# Copy wrapper scripts
copy sesame.bat dist\sesame-cli\
copy sesame.ps1 dist\sesame-cli\
copy sesame dist\sesame-cli\
```

### Step 3: Create Launcher Batch File

Create `sesame-cli\sesame.bat`:

```batch
@echo off
REM Sesame CLI Launcher
REM No Python installation required

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Activate venv and run CLI
call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
python "%SCRIPT_DIR%cli.py" %*

endlocal
```

### Step 4: Create Shortcut (Optional)

Create a Windows shortcut to `sesame.bat` and place on Desktop or Start Menu.

### Step 5: Test

```bash
cd dist\sesame-cli
sesame.bat get
sesame.bat list
sesame.bat add
```

---

## Advanced Method: PyInstaller with Collect-All

If you want a true single EXE, use this approach:

```bash
# Install dependencies
pip install pyinstaller

# Build with --collect-all
pyinstaller --onefile --collect-all keyring --collect-all cryptography --collect-all inquirer cli.py
```

However, this may still have issues with Windows Credential Manager access.

---

## Recommended: Portable Package

The best approach is to create a portable package:

```
sesame-cli/
├── sesame.bat          # Main launcher
├── sesame.ps1          # PowerShell launcher
├── sesame              # Bash launcher
├── cli.py              # CLI entry point
├── app/                # Application code
├── .venv/              # Virtual environment
└── README.txt          # Instructions
```

**Advantages:**
- ✅ No Python installation required
- ✅ All dependencies included
- ✅ Works with Windows Credential Manager
- ✅ Cross-platform (Windows/Linux/macOS)
- ✅ Easy to distribute

**Size:** ~200-300 MB (due to venv)

---

## Distribution

### Option A: ZIP File

```bash
# Create ZIP
powershell Compress-Archive -Path dist\sesame-cli -DestinationPath dist\sesame-cli.zip

# Users extract and run:
# sesame.bat get
```

### Option B: Installer (NSIS)

Create a Windows installer using NSIS:

```nsis
; sesame-cli-installer.nsi
Name "Sesame CLI"
OutFile "sesame-cli-setup.exe"
InstallDir "$PROGRAMFILES\Sesame CLI"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\sesame-cli\*.*"
  CreateDirectory "$SMPROGRAMS\Sesame CLI"
  CreateShortCut "$SMPROGRAMS\Sesame CLI\Sesame.lnk" "$INSTDIR\sesame.bat"
SectionEnd
```

### Option C: Portable EXE (Using Batch Compiler)

Use Batch Compiler to convert `sesame.bat` to `.exe`:
- Download: https://www.battoexeconverter.com/
- Convert `sesame.bat` to `sesame.exe`
- Users just run `sesame.exe get`

---

## Quick Setup for Users

### Windows

1. Download `sesame-cli.zip`
2. Extract to `C:\Program Files\Sesame CLI`
3. Add to PATH or create shortcut
4. Run: `sesame.bat get`

### Linux/macOS

1. Download and extract
2. `chmod +x sesame`
3. `sudo ln -s /path/to/sesame /usr/local/bin/sesame`
4. Run: `sesame get`

---

## Summary

| Method | Size | Complexity | Portability |
|--------|------|-----------|-------------|
| Portable Package (venv) | 200-300 MB | Easy | ⭐⭐⭐ |
| PyInstaller EXE | 50-100 MB | Hard | ⭐⭐ |
| Batch Compiler EXE | 200-300 MB | Medium | ⭐⭐⭐ |
| Installer (NSIS) | 50-100 MB | Hard | ⭐⭐⭐ |

**Recommendation:** Use **Portable Package** (venv-based) for maximum compatibility and ease of distribution.

---

## Create Portable Package (Step-by-Step)

### Windows PowerShell

```powershell
# 1. Create dist folder
New-Item -ItemType Directory -Path dist\sesame-cli -Force

# 2. Copy files
Copy-Item cli.py dist\sesame-cli\
Copy-Item app dist\sesame-cli\app -Recurse -Force
Copy-Item .venv dist\sesame-cli\.venv -Recurse -Force
Copy-Item sesame.bat dist\sesame-cli\
Copy-Item sesame.ps1 dist\sesame-cli\
Copy-Item sesame dist\sesame-cli\

# 3. Create README
@"
# Sesame CLI - Portable

## Usage

### Windows
sesame.bat get
sesame.bat list
sesame.bat add

### Linux/macOS
./sesame get
./sesame list
./sesame add

## First Time Setup

### Windows
- Just run sesame.bat

### Linux/macOS
chmod +x sesame
sudo ln -s $(pwd)/sesame /usr/local/bin/sesame
"@ | Out-File dist\sesame-cli\README.txt

# 4. Create ZIP
Compress-Archive -Path dist\sesame-cli -DestinationPath dist\sesame-cli.zip

# 5. Done!
Write-Host "Created: dist\sesame-cli.zip"
```

### Linux/macOS Bash

```bash
# 1. Create dist folder
mkdir -p dist/sesame-cli

# 2. Copy files
cp cli.py dist/sesame-cli/
cp -r app dist/sesame-cli/
cp -r .venv dist/sesame-cli/
cp sesame dist/sesame-cli/
cp sesame.ps1 dist/sesame-cli/

# 3. Create README
cat > dist/sesame-cli/README.txt << 'EOF'
# Sesame CLI - Portable

## Usage

### Linux/macOS
./sesame get
./sesame list
./sesame add

### Windows
sesame.bat get
sesame.bat list
sesame.bat add

## First Time Setup

### Linux/macOS
chmod +x sesame
sudo ln -s $(pwd)/sesame /usr/local/bin/sesame
EOF

# 4. Create ZIP
cd dist
zip -r sesame-cli.zip sesame-cli/
cd ..

# 5. Done!
echo "Created: dist/sesame-cli.zip"
```

---

## Result

After running the above, you'll have:

```
dist/
├── sesame-cli/          # Portable package
│   ├── sesame.bat       # Windows launcher
│   ├── sesame           # Linux/macOS launcher
│   ├── cli.py
│   ├── app/
│   ├── .venv/
│   └── README.txt
└── sesame-cli.zip       # Distributable ZIP
```

Users can now:
1. Download `sesame-cli.zip`
2. Extract anywhere
3. Run `sesame.bat` (Windows) or `./sesame` (Linux/macOS)

No Python installation required! 🎉
