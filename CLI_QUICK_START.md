# Sesame CLI - Quick Start

## Setup (One-time)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install click if not already installed
pip install click
```

## Basic Usage

### 1. List all credentials
```bash
python cli.py list
```

### 2. Get credential with interactive wizard
```bash
# Show all credentials and select one
python cli.py get

# Filter by tag(s) first, then select
python cli.py get gmail
python cli.py get gmail work

# Filter by category
python cli.py get -c Work
```

**Interactive flow:**
1. Credentials matching your filter are displayed as a numbered list
2. Enter the number to select
3. Choose to copy [p]assword or [u]sername
4. Password is copied to clipboard
5. **30-second countdown** starts - clipboard auto-clears after

### 3. Copy username instead of password
```bash
python cli.py get gmail -u
```

### 4. Show password in console (no copy)
```bash
python cli.py get gmail -s
```

### 5. Add new credential
```bash
# Interactive mode (prompts for each field)
python cli.py add

# Or with options
python cli.py add -n "Gmail" -u "user@gmail.com" -c "Email" -t "google,email"
```

### 6. Generate password
```bash
# Default: 16 chars, letters + digits
python cli.py generate

# Custom: 32 chars with special characters
python cli.py generate -l 32 --special
```

### 7. Delete credential
```bash
python cli.py delete "Gmail"
```

### 8. Export vault (backup)
```bash
python cli.py export -o backup.sesame
# Prompts for export password
```

### 9. Import vault (restore)
```bash
python cli.py import backup.sesame
# Prompts for import password
```

## Examples

```bash
# Get work email password
python cli.py get work email

# List all VPS credentials
python cli.py list -t vps

# Copy username for Gmail
python cli.py get gmail -u

# Show password without copying
python cli.py get gmail -s

# Generate strong password
python cli.py generate -l 32 --special

# Backup vault
python cli.py export -o C:\Users\YourName\Desktop\sesame-backup.sesame

# Restore vault
python cli.py import C:\Users\YourName\Desktop\sesame-backup.sesame
```

## Tips

- **AND logic for tags**: `python cli.py get gmail work` shows only credentials with BOTH tags
- **Multiple categories**: Use `-c` flag to filter by category
- **JSON output**: `python cli.py list --json` for scripting
- **Help**: `python cli.py --help` or `python cli.py <command> --help`

## Troubleshooting

**"ModuleNotFoundError: No module named 'click'"**
```bash
pip install click
```

**Clipboard not working on Linux**
```bash
# Install xclip
sudo apt install xclip
```

**Master password prompt appears**
- Your category is protected by master password
- Enter the master password when prompted
- You only need to enter it once per session
