# Quick Setup: `sesame` Command

## For Windows Users (Quickest)

### Step 1: Open PowerShell as Administrator

Press `Win + X`, select "Windows PowerShell (Admin)"

### Step 2: Enable Script Execution (One-time)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Add Alias to PowerShell Profile

```powershell
# Open your PowerShell profile
notepad $PROFILE

# Add this line at the end (replace with your actual path):
Set-Alias -Name sesame -Value "D:\workspace\sesame\sesame.ps1"

# Save and close
```

### Step 4: Reload PowerShell

Close and reopen PowerShell, then test:

```powershell
sesame --help
sesame list
sesame get
```

---

## For Linux/macOS Users

### Step 1: Make Script Executable

```bash
chmod +x ~/sesame/sesame
```

### Step 2: Create Symlink

```bash
# Option A: Using symlink (recommended)
sudo ln -s ~/sesame/sesame /usr/local/bin/sesame

# Option B: Copy to PATH
sudo cp ~/sesame/sesame /usr/local/bin/sesame
```

### Step 3: Test

```bash
sesame --help
sesame list
sesame get
```

---

## Usage

Once set up, use anywhere:

```bash
sesame get              # Interactive wizard
sesame get vps          # Filter by tag
sesame list             # List all
sesame add              # Add credential
sesame generate         # Generate password
sesame export -o backup.sesame
sesame import backup.sesame
```

---

## If Something Goes Wrong

### Windows - "cannot be loaded because running scripts is disabled"
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows - sesame not found
1. Make sure PowerShell profile was saved correctly
2. Restart PowerShell completely
3. Check path is correct in profile

### Linux/macOS - Permission denied
```bash
chmod +x /path/to/sesame/sesame
```

### Linux - xclip not found
```bash
sudo apt install xclip
```

---

## Verify It Works

```bash
sesame --help
sesame list
sesame get vps
```

Done! 🎉
