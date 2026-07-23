# Sesame CLI - Interactive Features Summary

## Overview

Sesame CLI now includes **interactive wizard** with live search and arrow key navigation, exactly as requested:

> "Khi gõ get tagx, khi đang gõ hệ thống tự hiển thị tìm kiếm và cho ngay kết quả live bên dưới, sau đó dùng mũi tên đi lên đi xuống và enter để chọn được không"

**Answer: YES! ✅**

## Interactive Workflow

### 1. Tag Selection (when no tags provided)

```bash
$ python cli.py get
```

**Display:**
```
Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)
❯ git
  hmt.ovh
  polarion
  uat
  vps
```

**Controls:**
- ↑↓ - Navigate through tags
- Space - Toggle tag selection (✓ appears when selected)
- Enter - Confirm and proceed to credential selection

### 2. Credential Selection (with live search)

**After selecting tags or providing them as arguments:**

```bash
$ python cli.py get vps
```

**Display:**
```
Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]
```

**Controls:**
- ↑↓ - Navigate through credentials
- Type - **Live search** (filters credentials in real-time)
- Enter - Select highlighted credential

**Example of live search:**
```
Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]

# User types "silv"
Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Silverbullet (hmt) [vps, hmt.ovh]

# Filtered to show only matching credentials
```

### 3. Credential Details & Copy

**After selecting a credential:**

```
📝 Silverbullet
   Username: hmt
   URL: https://notes.hmt.ovh
   Tags: vps, hmt.ovh

Copy [p]assword or [u]sername? [p]: p
✓ Password copied to clipboard
⏱️  Clearing clipboard in 30s...
⏱️  Clearing clipboard in 29s...
...
✓ Clipboard cleared.
```

## Features Implemented

### ✅ Live Search
- Type to filter credentials in real-time
- Matches against: name, username, tags
- Instant feedback as you type

### ✅ Arrow Key Navigation
- ↑↓ to navigate up/down
- Smooth scrolling through options
- Visual highlight of current selection

### ✅ Interactive Tag Selection
- Checkbox-style selection with Space key
- Multiple tag support (AND logic)
- All available tags displayed

### ✅ 30-Second Countdown
- Password auto-clears from clipboard
- Real-time countdown display
- Cross-platform support

### ✅ Fallback Support
- If inquirer not available, falls back to simple numbered selection
- Graceful degradation

## Usage Patterns

### Pattern 1: Full Interactive Flow
```bash
python cli.py get
# → Select tags → Select credential → Copy
```

### Pattern 2: With Tag Filter
```bash
python cli.py get vps
# → Select credential → Copy
```

### Pattern 3: With Multiple Tags (AND logic)
```bash
python cli.py get vps hmt.ovh
# → Select credential → Copy
```

### Pattern 4: With Category Filter
```bash
python cli.py get -c Private
# → Select tags → Select credential → Copy
```

### Pattern 5: Copy Username
```bash
python cli.py get vps -u
# → Select credential → Copy username
```

### Pattern 6: Show Password (no copy)
```bash
python cli.py get vps -s
# → Select credential → Display password
```

## Technical Implementation

### Libraries Used
- **click** - CLI framework
- **inquirer** - Interactive selection with live search
- **blessed** - Terminal formatting
- **readchar** - Keyboard input handling

### Key Classes
- `CredentialWizard` - Handles interactive selection
  - `select_tags()` - Tag selection with checkboxes
  - `select_credential()` - Credential selection with live search
  - `copy_credential()` - Copy with countdown

### Cross-Platform Clipboard
- **Windows**: Native `clip` command
- **Linux**: `xclip` or `xsel`
- **macOS**: Native `pbcopy`

## Installation

```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (including inquirer)
pip install -r requirements.txt
```

## Testing

All features tested and working:
- ✅ Tag selection with arrow keys
- ✅ Credential selection with live search
- ✅ Multiple tag selection (AND logic)
- ✅ 30-second countdown
- ✅ Cross-platform clipboard
- ✅ Fallback selection when inquirer unavailable

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ↑↓ | Navigate up/down |
| Space | Toggle selection (tag mode) |
| Type | Live search (credential mode) |
| Enter | Confirm selection |
| Ctrl+C | Cancel |

## Examples

### Example 1: Get VPS credential
```bash
$ python cli.py get vps

Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]

# Press Down arrow
Select credential (use ↑↓ arrows, type to search, Enter to select)
  Youtube Monitor (admin) [vps, hmt.ovh]
❯ Silverbullet (hmt) [vps, hmt.ovh]

# Press Enter
📝 Silverbullet
   Username: hmt
   URL: https://notes.hmt.ovh
   Tags: vps, hmt.ovh

Copy [p]assword or [u]sername? [p]: p
✓ Password copied to clipboard
⏱️  Clearing clipboard in 30s...
```

### Example 2: Full interactive flow
```bash
$ python cli.py get

Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)
❯ git
  hmt.ovh
  polarion
  uat
  vps

# Press Down arrow twice to reach 'vps'
Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)
  git
  hmt.ovh
  polarion
  uat
❯ vps

# Press Space to select
Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)
  git
  hmt.ovh
  polarion
  uat
❯ ✓ vps

# Press Enter to confirm
Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]

# Type to search
Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Silverbullet (hmt) [vps, hmt.ovh]

# Press Enter to select
📝 Silverbullet
   Username: hmt
   URL: https://notes.hmt.ovh
   Tags: vps, hmt.ovh

Copy [p]assword or [u]sername? [p]: p
✓ Password copied to clipboard
⏱️  Clearing clipboard in 30s...
```

## Summary

The Sesame CLI now provides a **modern, interactive experience** with:
- ✅ Live search as you type
- ✅ Arrow key navigation
- ✅ Visual feedback
- ✅ 30-second password countdown
- ✅ Cross-platform support
- ✅ Graceful fallbacks

All exactly as requested! 🎉
