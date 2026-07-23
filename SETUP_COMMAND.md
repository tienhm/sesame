# Setup `sesame` Command

Make it easy to run Sesame CLI from anywhere using just `sesame get`, `sesame list`, etc.

## Windows Setup

### Option A: Using PowerShell (Recommended)

1. **Create an alias in PowerShell profile:**

```powershell
# Open PowerShell profile
notepad $PROFILE

# Add this line (replace with your actual path)
Set-Alias -Name sesame -Value "C:\path\to\sesame\sesame.ps1"

# Save and reload profile
. $PROFILE
```

2. **Now use:**
```powershell
sesame get
sesame list
sesame add
```

### Option B: Using Batch File

1. **Add sesame folder to PATH:**
   - Open "Environment Variables" (search in Start menu)
   - Click "Edit the system environment variables"
   - Click "Environment Variables..." button
   - Under "User variables", click "New..."
   - Variable name: `PATH`
   - Variable value: `C:\path\to\sesame` (your sesame folder)
   - Click OK

2. **Now use from any folder:**
```cmd
sesame get
sesame list
sesame add
```

### Option C: Using Python Entry Point (Most Professional)

Create `sesame.exe` using PyInstaller:

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Create executable
pyinstaller --onefile --name sesame cli.py

# The executable will be in dist/sesame.exe
# Add dist folder to PATH or move sesame.exe to a folder in PATH
```

---

## Linux/macOS Setup

### Option A: Using Symlink (Recommended)

```bash
# Make script executable
chmod +x /path/to/sesame/sesame

# Create symlink in /usr/local/bin
sudo ln -s /path/to/sesame/sesame /usr/local/bin/sesame

# Now use from anywhere
sesame get
sesame list
sesame add
```

### Option B: Using PATH

```bash
# Make script executable
chmod +x /path/to/sesame/sesame

# Add to PATH in ~/.bashrc or ~/.zshrc
echo 'export PATH="/path/to/sesame:$PATH"' >> ~/.bashrc

# Reload shell
source ~/.bashrc

# Now use
sesame get
```

### Option C: Using Alias

```bash
# Add to ~/.bashrc or ~/.zshrc
alias sesame='/path/to/sesame/sesame'

# Reload shell
source ~/.bashrc

# Now use
sesame get
```

---

## Usage Examples

Once set up, you can use:

```bash
# Get credential with interactive wizard
sesame get

# Filter by tag
sesame get vps

# Filter by multiple tags
sesame get vps hmt.ovh

# Filter by category
sesame get -c Private

# Copy username
sesame get vps -u

# Show password (no copy)
sesame get vps -s

# List credentials
sesame list

# List with filters
sesame list -c Work -t email

# Add credential
sesame add

# Generate password
sesame generate -l 32 --special

# Export vault
sesame export -o backup.sesame

# Import vault
sesame import backup.sesame

# Get help
sesame --help
sesame get --help
```

---

## Troubleshooting

### Windows - PowerShell says "cannot be loaded because running scripts is disabled"

```powershell
# Run this once to enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows - sesame command not found

Make sure the folder is added to PATH and you've restarted your terminal.

### Linux/macOS - Permission denied

```bash
chmod +x /path/to/sesame/sesame
```

### Linux - xclip not found

```bash
# Install xclip for clipboard support
sudo apt install xclip
```

---

## Recommended Setup

### Windows
**Best**: PowerShell alias (Option A)
- Works in PowerShell
- Easy to set up
- No admin required

### Linux/macOS
**Best**: Symlink (Option A)
- Works in any shell
- Easy to set up
- Standard Unix approach

---

## Advanced: Create Global `sesame` Command

### Windows (Admin)

1. Create `sesame.bat` in `C:\Windows\System32\` or any folder in PATH
2. Content:
```batch
@echo off
python "C:\path\to\sesame\cli.py" %*
```

### Linux/macOS

```bash
# Create symlink in /usr/local/bin
sudo ln -s /path/to/sesame/sesame /usr/local/bin/sesame

# Or copy the script
sudo cp /path/to/sesame/sesame /usr/local/bin/sesame
sudo chmod +x /usr/local/bin/sesame
```

---

## Verify Installation

```bash
# Should show help
sesame --help

# Should show version/commands
sesame

# Should work
sesame list
```

Done! Now you can use `sesame get` from anywhere! 🎉
