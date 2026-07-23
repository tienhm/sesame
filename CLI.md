# Sesame CLI

A command-line interface for Sesame password manager. Works on **Windows**, **Linux**, and **macOS**.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Get credentials (Interactive wizard with live search)

```bash
# Interactive tag selection + credential selection
python cli.py get

# Filter by tag(s) - AND logic (skip tag selection)
python cli.py get gmail
python cli.py get gmail work

# Filter by category
python cli.py get -c Work

# Copy username instead of password
python cli.py get gmail -u

# Show password in console (no copy)
python cli.py get gmail -s
```

**Interactive flow (when no tags provided):**
1. **Tag selection** - Use ↑↓ arrows to navigate, Space to toggle, Enter to confirm
2. **Credential selection** - Use ↑↓ arrows to navigate, type to search, Enter to select
3. Choose to copy password or username
4. Password is copied to clipboard with **30-second countdown**
5. Clipboard is automatically cleared after countdown

**Keyboard controls:**
- **↑↓** - Navigate up/down
- **Space** - Toggle tag selection (checkbox mode)
- **Type** - Live search credentials
- **Enter** - Confirm selection
- **Ctrl+C** - Cancel

### List credentials

```bash
# List all
python cli.py list

# Filter by category
python cli.py list -c Work

# Filter by tags (AND logic)
python cli.py list -t gmail -t work

# Output as JSON
python cli.py list --json
```

### Add credential

```bash
python cli.py add
# Interactive prompts for:
# - Name (required)
# - Username (optional)
# - Secret/Password (required, hidden input)
# - URL (optional)
# - Category (default: General)
# - Tags (comma-separated, optional)

# Or with options:
python cli.py add -n Gmail -u user@gmail.com -c Email -t google,email
```

### Delete credential

```bash
python cli.py delete <entry-id-or-name>
```

### Generate password

```bash
# Default: 16 chars, letters + digits
python cli.py generate

# Custom length
python cli.py generate -l 32

# Include special characters
python cli.py generate -l 16 --special
```

### Export vault

```bash
python cli.py export -o backup.sesame
# Prompts for export password (confirmed)
```

### Import vault

```bash
python cli.py import backup.sesame
# Prompts for import password
```

## Features

✅ **Interactive wizard** — select credentials from numbered list  
✅ **Tag filtering** — AND logic for multiple tags  
✅ **Category filtering** — organize by category  
✅ **30-second countdown** — automatic clipboard clear for passwords  
✅ **Cross-platform** — Windows, Linux, macOS  
✅ **Secure storage** — uses Windows Credential Manager (Windows) or Secret Service (Linux)  
✅ **Master password** — optional protection per category  
✅ **Export/Import** — AES-256-GCM encrypted `.sesame` files  

## Clipboard Support

- **Windows**: Uses native `clip` command
- **Linux**: Uses `xclip` or `xsel` (install if needed: `sudo apt install xclip`)
- **macOS**: Uses native `pbcopy` command
- **Fallback**: Optional `pyperclip` library (install: `pip install pyperclip`)

## Examples

```bash
# Get Gmail password interactively
python cli.py get gmail

# Get work credentials with multiple tags
python cli.py get work email -c Work

# Copy username instead
python cli.py get gmail -u

# Show password without copying
python cli.py get gmail -s

# List all work credentials
python cli.py list -c Work

# Add new credential
python cli.py add -n "AWS Console" -u admin@company.com -c Work -t aws,cloud

# Generate 32-char password with special chars
python cli.py generate -l 32 --special

# Backup vault
python cli.py export -o ~/sesame-backup.sesame

# Restore vault
python cli.py import ~/sesame-backup.sesame
```

## Security Notes

- Secrets are **never** displayed in console (unless `--show` flag)
- Passwords are copied to clipboard with **30-second auto-clear**
- All data stored in Windows Credential Manager (DPAPI-encrypted on Windows)
- Export files are **AES-256-GCM encrypted** with PBKDF2-derived keys
- Master password uses **PBKDF2-HMAC-SHA256** (600k iterations)

## Troubleshooting

**Clipboard not working on Linux?**
```bash
# Install xclip
sudo apt install xclip

# Or install pyperclip
pip install pyperclip
```

**Master password prompt not appearing?**
- Category is protected by master password
- Run `python cli.py get <tag>` and enter master password when prompted

**Import fails?**
- Check password is correct
- Ensure `.sesame` file is not corrupted
- Try importing on the same machine it was exported from
