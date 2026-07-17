# Sesame  `v1.1`

> **Se**crets **Sa**fe **Me**moriser

A lightweight Windows desktop application for quick access to frequently used passwords and secrets, displayed through a floating bubble that stays on top of all windows.

No administrator privileges required. Suitable for standard corporate user accounts.

---

## Features

- **Floating bubble** — small always-on-top button, draggable to any screen position, remembers position between sessions
- **Vault panel** — title bar with ⊙ restore and ✕ close; draggable by the caption; real-time search, category filter, and tag filter
- **Tags** — attach multiple comma-separated tags to each entry; filter by one or more tags (AND logic) using the left panel
- **URL field** — optional URL per entry; shown as a clickable link that opens the default browser
- **Copy to clipboard** — 👤 copies username (flash feedback), 🔑 copies password with 30-second auto-clear countdown; neither is stored in Windows Clipboard History (Win+V)
- **In-row edit** — ✏️ button on each entry opens the edit dialog directly; existing secret is pre-loaded
- **Password generator** — 🎲 button in the edit dialog opens a generator with configurable length, character sets (letters, digits, special); options are remembered between opens
- **Single instance** — launching a second instance (or using *Locate Sesame* in the tray) signals the first to flash the bubble at screen centre
- **Categories** — organize entries into named groups; rename or delete via Settings
- **Default category** — configure a category to be pre-selected on startup
- **Background image** — set a custom photo as the panel background; drag the viewport to choose which region to display; adjust component opacity so the image shows through the UI
- **Settings** — single dialog covering General (opacity, background image, default category), Categories, and Security
- **Master password** — optionally protect one or more categories with a shared master password; prompted once per session
- **Start with Windows** — enabled by default; toggle from Settings (no admin required)
- **Secure storage** — secrets stored in Windows Credential Manager (DPAPI-encrypted, tied to your Windows account)
- **Export / Import** — back up the entire vault to an encrypted `.sesame` file; restore it on any machine using a password you choose

---

## Requirements

- Windows 10 / 11
- Python 3.11+ (for running from source)

---

## Installation

### Option A — Run from source

```powershell
# 1. Clone the repository
git clone <repo-url>
cd sesame

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

### Option B — Build a standalone executable

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pyinstaller sesame.spec
```

The output is `dist/Sesame.exe` — a single file, no installation needed, no admin rights required.

---

## Project Structure

```
sesame/
├── main.py                  # Application entry point and controller
├── app/
│   ├── config.py            # User preferences → %APPDATA%\Sesame\config.json
│   ├── bubble.py            # Floating always-on-top draggable button
│   ├── vault_panel.py       # Main panel: search, tag filter, entry list
│   ├── tray.py              # System tray icon and context menu
│   ├── dialogs/
│   │   ├── add_entry.py     # Add / Edit entry dialog
│   │   ├── export_import.py # Export / Import vault dialogs
│   │   └── settings.py      # Settings dialog (General, Categories, Security)
│   ├── models/
│   │   ├── entry.py         # Entry dataclass (id, name, username, url, tags, category)
│   │   └── vault.py         # CRUD operations via Windows Credential Manager
│   └── utils/
│       ├── clipboard.py     # Copy to clipboard + auto-clear after 30 s
│       ├── lock_manager.py  # Master password lock per category
│       ├── startup.py       # Windows startup registry helper
│       └── vault_io.py      # AES-256-GCM encrypt/decrypt for export files
├── resources/
│   ├── icon.png
│   └── style.qss            # Dark theme stylesheet
├── requirements.txt
└── sesame.spec              # PyInstaller build spec
```

---

## How it works

### Storage

Secrets are never written to disk in plaintext.

| What | Where |
|---|---|
| Entry metadata (name, username, url, tags, category) | `%APPDATA%\Sesame\sesame_vault.json` — plain JSON, no secrets |
| Each secret | Individual Credential Manager entry — `TargetName` = `SZM:<entry-id>`, `UserName` = "" |
| UI preferences (bubble position, default category, master password hash) | `%APPDATA%\Sesame\config.json` — no secrets here |

`entry-id` is a short, reused-gap integer assigned locally by the vault (not a global UUID), keeping each Credential Manager entry compact. `UserName` is left empty — the actual account username is stored in `sesame_vault.json`, not duplicated into Credential Manager. Secrets from older versions are migrated to this layout automatically the first time they're read.

Windows DPAPI encrypts all Credential Manager entries automatically. The data is tied to the current Windows user account and machine.

### Tags & filtering

Each entry can have multiple tags (comma-separated in the edit dialog). The left panel shows:
- A **category combo box** at the top — filters the tag list and entry list by category
- A **tag list** below — shows only tags present in the selected category; supports multi-select

Selecting multiple tags applies **AND logic** — only entries that contain all selected tags are shown. The search bar also matches against tag names.

### Master password

One shared master password can protect any number of categories. Protected categories require the password once per session before copying is allowed. The password is stored as a salted PBKDF2-HMAC-SHA256 hash in `config.json` — the plaintext is never saved.

Configure in **Settings → Security**:
- **Set / Change…** — set a new master password (requires current password if one already exists)
- **Remove…** — remove the master password (requires current password)
- Checkboxes — enable or disable protection per category (only available once a master password is set)

### Export / Import

The vault can be exported to a portable `.sesame` file for backup or migration to another machine.

- **Export** — tray menu → *Export Vault…* — enter a password (confirmed), choose a save location. All entries and their secrets are serialised to JSON, encrypted with **AES-256-GCM**, and written to the file. The encryption key is derived from your password using **PBKDF2-HMAC-SHA256** (600 000 iterations, random 16-byte salt).
- **Import** — tray menu → *Import Vault…* — select the `.sesame` file, enter the password. Entries are added to the current vault. Incorrect passwords are rejected with an error message; the file is never modified.

The `.sesame` file is safe to copy or email — it is unreadable without the correct password.

### Start with Windows

Uses `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` — a user-level registry key that does not require administrator privileges.

The entry is created automatically on first launch. It can be toggled in **Settings → General**.

### Clipboard auto-clear

When you click 🔑 on an entry:

1. The secret is placed on the clipboard, **excluded from Windows Clipboard History** (Win+V).
2. A 30-second countdown appears on the button — and on the bubble if the panel is closed.
3. After 30 seconds the clipboard is cleared automatically.

Clicking 👤 copies the username (also excluded from Win+V) — a brief ✓ flash confirms the copy.

---

## Usage

### First launch

1. The bubble appears in the bottom-right corner of the screen.
2. Click it to open the vault panel.
3. Click **+ Add** to create your first entry.

### Adding an entry

Fill in **Name** (required), **Username** (optional), **Secret** (required), **URL** (optional), **Tags** (optional, comma-separated), and select or type a **Category**. Click **Save**.

Use the **👁** button to reveal/hide the secret, and **🎲** to open the password generator.

### Password generator

Click **🎲** next to the secret field to open the generator:
- Set the desired **length** (4–64 characters)
- Choose character sets: **Letters**, **Digits**, **Special characters**
- The password updates live as you adjust options
- Click **↻** to generate a new one with the same settings
- **Use this password** applies it; **Cancel** discards

Options are remembered for the session.

### Entry row buttons

| Button | Action |
|---|---|
| 👤 | Copy username to clipboard (no auto-clear, brief ✓ feedback) |
| 🔑 | Copy password/secret to clipboard (30 s auto-clear countdown) |
| ✏️ | Open edit dialog (existing secret pre-loaded) |

### Tag filtering

1. Select a category from the combo box — the tag list updates to show only relevant tags.
2. Click one or more tags to filter entries — multiple tags use AND logic.
3. Click a selected tag again to deselect it.

### Moving the bubble

Click and drag the bubble to any position on screen. The position is saved automatically.

### Panel caption bar

The panel has a title bar at the top with two buttons on the right:

| Button | Action |
|---|---|
| ⊙ | Restore to bubble mode — hides panel, shows bubble at the button's position |
| ✕ | Close panel — panel hides, bubble stays hidden, app runs in tray |

Drag the title bar to reposition the panel. The ⊙ and ✕ buttons in the toolbar (bottom right) also provide quick access.

### Background image

In **Settings → General**:
1. Click **Browse…** to select a photo (PNG, JPG, BMP, WebP).
2. Drag the blue viewport rectangle to choose which region of the image is displayed in the panel.
3. Use the **Components opacity** slider to make the UI elements (search bar, lists, buttons) semi-transparent so the image shows through.
4. Click **Clear** to remove the background.

### System tray

Right-click the tray icon for quick access to:

| Item | Action |
|---|---|
| Show Bubble / Hide Bubble | Toggle the floating bubble (disabled while panel is open) |
| Locate Sesame | Flash the bubble at screen centre |
| ❤ Support Sesame | Open the sponsor page |
| Exit Sesame | Quit the app |

---

## Dependencies

| Package | Purpose |
|---|---|
| `PySide6` | Qt6 UI framework (LGPL) |
| `keyring` | Vault-index migration only (secrets use `pywin32` directly, see Storage) |
| `pywin32` | Direct Windows Credential Manager access for secrets (Windows only) |
| `cryptography` | AES-256-GCM encryption for vault export; PBKDF2 for master password |
| `pillow` | PNG → ICO conversion for PyInstaller (build only) |
| `pyinstaller` | Package to standalone `.exe` (build only) |

---

## Corporate environment notes

- No administrator privileges required at any point.
- No files written outside `%APPDATA%\Sesame\` and Windows Credential Manager.
- No network access. All data stays on the local machine.
- The `.exe` produced by PyInstaller is fully self-contained — no Python installation required on the target machine.
- The app does not appear in the taskbar (uses `Qt::Tool` window flag).
