# Sesame

> **Se**crets **Sa**fe **Me**moriser

A lightweight Windows desktop application for quick access to frequently used passwords and secrets, displayed through a floating bubble that stays on top of all windows.

No administrator privileges required. Suitable for standard corporate user accounts.

---

## Download & Run

1. Download the latest `Sesame-*.exe` from `dist/` (or from GitHub Releases).
2. Double-click the file — no installation is needed.
3. The floating bubble appears in the bottom-right corner.

To run or build from source, see [`DEV_GUIDE.md`](DEV_GUIDE.md).

---

## Features

- **Floating bubble** — small always-on-top button, draggable to any screen position, remembers position between sessions
- **Vault panel** — real-time search, category filter, and tag filter
- **Tags** — attach multiple comma-separated tags to each entry; filter by one or more tags (AND logic)
- **URL** — optional per entry; a small link icon opens the default browser
- **Auto-login** — set a delay per entry; after opening the URL, Sesame injects `username → TAB → password` as keystrokes (Windows only)
- **OTP / TOTP** — store a base32 TOTP secret per entry; live 6-digit code shown in the entry row, updated every second
- **Movement reminder** — configurable idle timer blinks the bubble orange to remind you to move; click to confirm or snooze
- **Copy to clipboard** — copy username or password; passwords auto-clear after 30 seconds and are excluded from Windows Clipboard History (Win+V)
- **Password generator** — configurable length and character sets, cryptographically secure
- **Master password** — protect selected categories; prompted once per session
- **Start with Windows** — enabled by default, no admin required
- **Export / Import** — backup and restore your vault with AES-256-GCM encrypted `.sesame` files

---

## Quick Start

### First launch

1. The bubble appears in the bottom-right corner of the screen.
2. Click it to open the vault panel.
3. Click **+ Add** to create your first entry.

### Adding an entry

Fill in **Name** (required), **Username** (optional), **Secret** (required), **URL** (optional), **Tags** (optional, comma-separated), and select a **Category**. Click **Save**.

Use the **👁** button to reveal/hide the secret, and **🎲** to open the password generator.

### Copy a password

Click the **🔑** button on an entry. The password is copied to the clipboard and will clear automatically after 30 seconds. The countdown is also shown on the bubble if the panel is closed.

### Tag filtering

1. Select a category from the combo box.
2. Click one or more tags to filter entries (AND logic).
3. Click a selected tag again to deselect it.

### Movement reminder

Enable it in **Settings → General** and choose an interval (5–120 minutes, default 20). When the timer expires, the bubble blinks orange and, after a short delay, starts roaming across the screen. Click the bubble to confirm or snooze for 5 minutes.

### System tray

Right-click the tray icon to show/hide the bubble, open Settings, locate Sesame, or exit.

---

## Security

- **Storage** — passwords and OTP secrets are stored in Windows Credential Manager (DPAPI-encrypted). Entry metadata is stored in `%APPDATA%\Sesame\sesame_vault.json` (no secrets).
- **Clipboard** — copied secrets are excluded from Windows Clipboard History (Win+V) and auto-clear after 30 seconds.
- **Master password** — stored as a salted PBKDF2-HMAC-SHA256 hash in `%APPDATA%\Sesame\config.json`.
- **Export** — `.sesame` files are encrypted with AES-256-GCM; the key is derived from your password with PBKDF2-HMAC-SHA256 (600 000 iterations).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Bubble does not appear | Right-click the tray icon and choose **Show Bubble**, or restart the app. |
| SmartScreen warning | Click **More info** → **Run anyway**. |
| Clipboard not clearing | Make sure no other app is actively using the clipboard. |
| Forgot master password | Remove it in **Settings → Security** (requires the current password). All category locks will be cleared. |

---

## Corporate / Locked-down Environment

- No administrator privileges required at any point.
- No files written outside `%APPDATA%\Sesame\` and Windows Credential Manager.
- No network access. All data stays on the local machine.
- The executable is self-contained — no Python installation required.

---

## Configuration

### Startup
- **Settings → General → Start with Windows** toggles whether Sesame launches at login. It uses a user-level registry key, so no admin rights are required.

### Movement Reminder
- **Settings → General → Remind me every X min** enables the idle timer (5–120 min, default 20).
- When the timer expires, the bubble blinks orange.
- If you do not click it, the bubble starts roaming across the screen after a short delay.
- Click the bubble to open the dialog:
  - **✓ I moved!** resets the timer.
  - **Remind me in 5 min** snoozes for 5 minutes.
- The reminder pauses and resets automatically when the system hibernates or sleeps.

### Master Password
- **Settings → Security → Set / Change…** creates or updates the master password.
- **Settings → Security → Remove…** removes it (requires current password).
- Checkboxes enable protection per category. Protected categories require the password once per session before copying is allowed.

### Background Image
1. **Settings → General → Browse…** select a PNG/JPG image.
2. Drag the blue viewport rectangle to choose which region is shown.
3. Use the **Components opacity** slider to make UI elements semi-transparent.
4. Click **Clear** to remove the background.

---

## Tray Icon Commands

Right-click the tray icon for quick access:

| Command | Description |
|---|---|
| Show Bubble / Hide Bubble | Toggle the floating bubble (disabled while panel is open) |
| Locate Sesame | Flash the bubble at screen centre |
| Settings | Open the Settings dialog |
| ❤ Support Sesame | Open the sponsor page |
| Exit Sesame | Quit the application |

---

## Export / Import

### Export Vault
1. **Settings → Data → Export Vault…**
2. Enter an encryption password and confirm it.
3. Choose a save location.
4. A `.sesame` file is created — it is safe to copy or back up.

### Import Vault
1. **Settings → Data → Import Vault…**
2. Select the `.sesame` file.
3. Enter the password.
4. Entries are added to the current vault. The original file is never modified.

---

## System Requirements

### Minimum
- Windows 10 or later
- 64-bit architecture
- 256 MB RAM
- 200 MB disk space

### Recommended
- Windows 11
- 512 MB+ RAM
- 300 MB disk space

---

## Notes

- **First run** may be slow (Windows caching). Subsequent runs are faster.
- **Windows SmartScreen** may show a warning; click **More info** → **Run anyway**.
- **Updates** require rebuilding the executable after code changes.
- **Backup** your vault periodically by exporting it.
- **Antivirus false positive** — Some engines may flag `Sesame-*.exe` because of PyInstaller. The source is open; build from source if in doubt.

---

## More Information

- [Developer Guide](DEV_GUIDE.md) — build from source, virtual environment, project structure, architecture, build/packaging, and security
