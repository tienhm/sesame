## Sesame v1.2

> **Se**crets **Sa**fe **Me**moriser

A lightweight Windows 64-bit desktop password manager. Stores secrets in Windows Credential Manager (DPAPI-encrypted). No installation required, no admin rights needed.

---

### What's new in v1.2

**Auto-login**
Set a delay (milliseconds) per entry. After clicking the URL, Sesame waits then injects `username → TAB → password` as keystrokes into the focused window. No trailing Enter — you verify focus before submitting. Windows only.

**Export / Import inline in Settings**
Password fields and file picker are now on the Settings → Data tab directly. No separate popup window.

**Compact credential storage**
Secrets are now stored via `win32cred` (pywin32) with short numeric IDs (`SZM:0`, `SZM:1`…) instead of UUIDs. Eliminates the silent save failures on corporate machines caused by the 2 560-byte Windows Credential Manager limit. Existing entries migrate automatically on first launch.

**Tag filter: single-select**
Click a tag to filter entries, click again to deselect.

**Tray menu improvements**
Left-click now opens the context menu. Dark theme matches the app.

---

### Features

**Core**
- Floating always-on-top bubble — drag to any position
- Vault panel — search, category filter, tag filter, drag-to-reorder entries
- Click ⊙ to restore bubble; click ✕ to close panel

**Entries**
- Fields: Name, Username, URL (clickable), Secret, Tags, Category
- Inline 👤 copy username / 🔑 copy password (30 s auto-clear, excluded from Win+V)
- Inline ✏ edit (pre-loads existing secret)
- 🎲 Password generator — length, letters/digits/special; remembers settings

**Security**
- Secrets in Windows Credential Manager (DPAPI-encrypted, per user)
- Master password (PBKDF2-HMAC-SHA256, 600 000 iterations) per category; unlocked once per session
- Clipboard excluded from Windows Clipboard History (Win+V)

**Settings**
- General: bubble opacity, default category, background image, component opacity
- Categories: rename, delete
- Security: master password management
- Data: export / import vault inline

**System tray**
- Show / Hide Bubble (context-aware)
- Locate Sesame — flash bubble at screen centre
- ❤ Support Sesame
- Exit

---

### Download

**Download zip (recommended):** `sesame-binary-w64.zip` — Password: `sesame`
**Download exe directly:** `Sesame.exe`

> ⚠️ Some antivirus engines may flag this exe — this is a **false positive** common with PyInstaller-packaged Python apps. The source code is fully open on this repository. If in doubt, build from source.
