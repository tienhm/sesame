# Build `sesame` Command - Complete Guide

## What Was Created

Three wrapper scripts to make `sesame get`, `sesame list`, etc. work from anywhere:

1. **`sesame.bat`** - Windows batch file
2. **`sesame.ps1`** - PowerShell script
3. **`sesame`** - Bash script (Linux/macOS)

---

## Windows Setup (3 Options)

### Option 1: PowerShell Alias (Easiest) ⭐

**Step 1:** Open PowerShell as Administrator
```powershell
# Press Win+X, select "Windows PowerShell (Admin)"
```

**Step 2:** Enable scripts (one-time)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Step 3:** Add alias to profile
```powershell
# Open profile
notepad $PROFILE

# Add this line (replace path):
Set-Alias -Name sesame -Value "D:\workspace\sesame\sesame.ps1"

# Save and close
```

**Step 4:** Reload and test
```powershell
# Close and reopen PowerShell
sesame get
sesame list
```

---

### Option 2: Add to PATH

**Step 1:** Open Environment Variables
- Search "Environment Variables" in Start menu
- Click "Edit the system environment variables"
- Click "Environment Variables..." button

**Step 2:** Add sesame folder to PATH
- Under "User variables", click "New..."
- Variable name: `PATH`
- Variable value: `D:\workspace\sesame`
- Click OK

**Step 3:** Restart terminal and test
```cmd
sesame get
sesame list
```

---

### Option 3: Create .exe (Most Professional)

```bash
# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --name sesame cli.py

# sesame.exe will be in dist/ folder
# Add dist/ to PATH or move to C:\Windows\System32\
```

---

## Linux/macOS Setup (2 Options)

### Option 1: Symlink (Recommended) ⭐

```bash
# Make executable
chmod +x ~/sesame/sesame

# Create symlink
sudo ln -s ~/sesame/sesame /usr/local/bin/sesame

# Test
sesame get
sesame list
```

---

### Option 2: Add to PATH

```bash
# Make executable
chmod +x ~/sesame/sesame

# Add to ~/.bashrc or ~/.zshrc
echo 'export PATH="~/sesame:$PATH"' >> ~/.bashrc

# Reload
source ~/.bashrc

# Test
sesame get
```

---

## Usage Examples

Once set up, use from anywhere:

```bash
# Interactive wizard
sesame get

# Filter by tag
sesame get vps

# Filter by multiple tags (AND logic)
sesame get vps hmt.ovh

# Filter by category
sesame get -c Private

# Copy username
sesame get vps -u

# Show password (no copy)
sesame get vps -s

# List all credentials
sesame list

# List with filters
sesame list -c Work -t email

# Add credential
sesame add

# Add with options
sesame add -n Gmail -u user@gmail.com -c Email -t google

# Generate password
sesame generate

# Generate 32-char password with special chars
sesame generate -l 32 --special

# Export vault
sesame export -o backup.sesame

# Import vault
sesame import backup.sesame

# Get help
sesame --help
sesame get --help
sesame list --help
```

---

## Verification

Test your setup:

```bash
# Should show help
sesame --help

# Should list credentials
sesame list

# Should start interactive wizard
sesame get
```

---

## Troubleshooting

### Windows - "cannot be loaded because running scripts is disabled"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows - sesame command not found
1. Verify path in PowerShell profile is correct
2. Restart PowerShell completely
3. Check file exists at that path

### Linux/macOS - Permission denied
```bash
chmod +x ~/sesame/sesame
```

### Linux - xclip not found (clipboard not working)
```bash
sudo apt install xclip
```

### macOS - zsh: command not found
```bash
# Add to ~/.zshrc instead of ~/.bashrc
echo 'export PATH="~/sesame:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## Files Created

```
sesame/
├── sesame.bat          # Windows batch wrapper
├── sesame.ps1          # PowerShell wrapper
├── sesame              # Bash wrapper (Linux/macOS)
├── QUICK_SETUP.md      # Quick setup guide
├── SETUP_COMMAND.md    # Detailed setup guide
└── BUILD_COMMAND.md    # This file
```

---

## Recommended Setup

| OS | Method | Difficulty | Recommendation |
|---|---|---|---|
| Windows | PowerShell Alias | Easy | ⭐ Best |
| Windows | Add to PATH | Medium | Good |
| Windows | Create .exe | Hard | Most professional |
| Linux | Symlink | Easy | ⭐ Best |
| Linux | Add to PATH | Easy | Good |
| macOS | Symlink | Easy | ⭐ Best |
| macOS | Add to PATH | Easy | Good |

---

## Summary

✅ **Windows**: Use PowerShell alias (easiest)  
✅ **Linux/macOS**: Use symlink (standard Unix approach)  
✅ **All platforms**: Works from any folder  
✅ **All commands**: `sesame get`, `sesame list`, `sesame add`, etc.  

Now you can use `sesame` command just like any other CLI tool! 🎉
