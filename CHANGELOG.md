# Changelog

## v1.2 — 2026-07-17

### Added
- **Auto-login** — set a delay (ms) per entry; after clicking the URL Sesame waits then injects `username → TAB → password` as keystrokes (Windows only, no trailing Enter so you verify focus first)
- **Export / Import inline in Settings → Data tab** — password fields and file picker directly on the form, no separate popup window
- **Export / Import in Settings** now accessible from the tray icon and the vault panel sponsor button

### Changed
- **Secrets stored via `win32cred` (pywin32)** — compact target name `SZM:<id>`, eliminates silent save failures on machines with the 2 560-byte Credential Manager limit
- **Entry IDs are now short integers** (0, 1, 2…) instead of UUIDs; existing entries migrate automatically on first launch
- **Tag filter is single-select** — click a tag to filter, click again to deselect and show all entries in the category
- **Tray icon left-click** opens the context menu (right-click still works)
- **Tray context menu** styled to match the dark app theme
- **Double-click tray** → Locate Sesame (flash bubble at screen centre)
- `flash_and_center` now hides the panel if open before flashing the bubble
- Selected tag/entry row is 30% more opaque than the component opacity setting

### Fixed
- `pywin32` missing from venv → `set_secret` crashed silently and secrets were not saved
- `CredentialBlob` type mismatch with pywin32 312 (bytes vs string)
- Export/Import dialog appeared behind Settings due to `WindowStaysOnTopHint` — redesigned as inline form
- UUID entry IDs automatically re-assigned to compact numeric IDs on first launch

---

## v1.1 — 2026-07-17

### Fixed
- **Vault index moved to file** (`%APPDATA%\Sesame\sesame_vault.json`) — resolves silent save failures on corporate machines (2 560-byte Credential Manager limit). Migrates automatically.
- Security review fixes: `remove_lock` typo, duplicate `itemChanged` signal connections, disconnected sponsor button, PBKDF2 iterations raised to 600 000, clipboard `clear()` via Win32 path, unclosed file handle, falsy-zero `or` bug, `random.choice` → `secrets.choice`, countdown badge on list rebuild

### Changed
- Tag list single-select; selected background 30% more opaque
- Drag-to-reorder entries; scale-aware viewport preview in Settings

---

## v1.0 — 2026-07-12

Initial release — floating bubble, vault panel, entry fields, clipboard auto-clear (Win+V excluded), master password, export/import (AES-256-GCM), background image, single instance, Font Awesome 6 icons.
