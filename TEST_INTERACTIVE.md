# Sesame CLI - Interactive Selection Test

## New Features

### 1. Interactive Tag Selection (when no tags provided)
```bash
python cli.py get
```

**Flow:**
1. Shows all available tags with checkboxes
2. Use ↑↓ arrow keys to navigate
3. Use Space to toggle tag selection
4. Press Enter to confirm selection
5. Then shows matching credentials with arrow key selection

### 2. Interactive Credential Selection
```bash
python cli.py get vps
```

**Flow:**
1. Filters credentials by tag 'vps'
2. Shows matching credentials
3. Use ↑↓ arrow keys to navigate
4. Press Enter to select
5. Shows credential details
6. Prompts to copy password or username

## Test Cases

### Test 1: No arguments (full interactive flow)
```bash
$ python cli.py get

Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)
❯ git
  hmt.ovh
  polarion
  uat
  vps

# Press Space on 'vps' to select
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

# Press Down arrow to select Silverbullet
Select credential (use ↑↓ arrows, type to search, Enter to select)
  Youtube Monitor (admin) [vps, hmt.ovh]
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

### Test 2: With tag argument (skip tag selection)
```bash
$ python cli.py get vps

Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]
```

### Test 3: With multiple tags (AND logic)
```bash
$ python cli.py get vps hmt.ovh

Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]
```

### Test 4: With category filter
```bash
$ python cli.py get -c Private

Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)
❯ git
  hmt.ovh
  vps

# Select vps
Select credential (use ↑↓ arrows, type to search, Enter to select)
❯ Youtube Monitor (admin) [vps, hmt.ovh]
  Silverbullet (hmt) [vps, hmt.ovh]
```

## Keyboard Controls

### Tag Selection (Checkbox)
- **↑↓** - Navigate up/down
- **Space** - Toggle selection
- **Enter** - Confirm selection
- **Ctrl+C** - Cancel

### Credential Selection (List)
- **↑↓** - Navigate up/down
- **Type** - Live search (filter credentials)
- **Enter** - Select highlighted credential
- **Ctrl+C** - Cancel

## Benefits

✅ **Live search** - Type to filter credentials in real-time  
✅ **Arrow key navigation** - Intuitive selection  
✅ **Multiple tag selection** - Easy multi-select with Space  
✅ **Visual feedback** - Checkmarks and highlights  
✅ **Fallback support** - Works even if inquirer not available  
✅ **Cross-platform** - Windows, Linux, macOS  
