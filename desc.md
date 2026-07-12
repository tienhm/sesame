## Sesame v1.0

> Open **Se**crets **Sa**fe **Me**moriser

A lightweight Windows desktop password manager. Stores secrets in Windows Credential Manager (DPAPI-encrypted). No installation required, no admin rights needed.

---

### Features

**Core**
- Floating always-on-top bubble — drag to any position, persists between sessions
- Vault panel with title bar — drag to reposition, ⊙ restores to bubble, ✕ closes to tray
- Bubble and panel are linked: click bubble to open panel, click ⊙ to return

**Entries**
- Fields: Name, Username, URL (clickable link), Secret, Tags, Category
- Inline copy buttons per row: 👤 username, 🔑 password (30-second auto-clear countdown)
- Inline edit button ✏ — pre-loads existing secret
- Password generator 🎲 with configurable length (4–64), character sets (letters / digits / special); remembers settings between opens; uses `secrets.choice` (cryptographically secure)
- Clipboard excluded from **Windows Clipboard History** (Win+V) via `ExcludeClipboardContentFromMonitorProcessing`
- Active countdown mirrors on the bubble when panel is closed

**Filtering**
- Category combo + tag list (AND logic multi-select)
- Real-time search across name, username, tags

**Security**
- Master password (PBKDF2-HMAC-SHA256, 600 000 iterations) protects selected categories; unlocked once per session

**Export / Import**
- AES-256-GCM encrypted `.sesame` files — PBKDF2-derived key, 600 000 iterations, random salt

**Settings**
- General: Start with Windows, default category, bubble opacity, background image with drag-to-position viewport, component opacity slider
- Categories: rename, delete
- Security: set / change / remove master password; per-category lock toggle

**System tray**
- Show / Hide Bubble (context-aware, disabled while panel is open)
- Locate Sesame — flashes bubble at screen centre
- ❤ Support Sesame
- Exit

**Other**
- Single-instance: second launch signals the first to flash the bubble
- Font Awesome 6 icons
- No network access; all data stays local

---

### Download

`Sesame.exe` — standalone executable, no Python required, no installation needed.
