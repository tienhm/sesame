# Changelog

## v1.4 — 2026-07-26

### Added
- **Movement reminder** — configurable idle timer (5–120 min, default 20) blinks the bubble orange when it's time to move; clicking it shows a dialog with a random motivational quote and "✓ I moved!" / "Remind me in 5 min" choices; paused/reset automatically on system hibernate/resume
- **Roaming bubble** — if the user doesn't interact with the blinking bubble, it starts roaming across the screen after a configurable delay to grab attention
- Settings → General → new "Movement reminder" section (enable checkbox + interval spinbox)
- **Settings** added to the system tray context menu

### Changed
- **Configuration centralization** — all UI sizing and timing constants (bubble size, drag threshold, panel size, caption height, movement badge size/intervals, clipboard timeout, countdown interval, auto-login inter-key delay, movement reminder default/snooze minutes, roaming delay/interval, OTP refresh interval, etc.) have been moved from hardcoded module constants into `_PROTECTED_CONFIG` in `app/config.py`
- Application code now reads these values from `AppConfig`, so user settings are preserved and protected even when `config.json` is overwritten

### Fixed
- **Standalone `.exe` build was missing `resources/` folder** (Font Awesome font, `style.qss`, `icon.png`) — PyInstaller spec had `datas=[]`, so the packaged exe showed missing icon glyphs (bubble/tray/buttons), no transparent background, and an unstyled UI. Fixed by adding all resource files to the `datas=` list in `sesame.spec`; PyInstaller automatically adjusts `__file__` inside the bundle so existing `os.path.dirname(__file__)` calls resolve correctly.
- **OTP codes stuck showing `● ● ●` (dots) in the packaged `.exe`** — `pyotp` and `win32timezone` (a `pywintypes`/`win32cred` runtime dependency used by Credential Manager access) are imported dynamically at call-time and were missed by PyInstaller's static analysis. Added both as `hiddenimports` in `sesame.spec`.
- **Output executable name** is now versioned as `dist/Sesame-v1.4.exe` from `sesame.spec`.

## v1.3 — 2026-07-20

### Added
- **TOTP / OTP support** — store a base32 TOTP secret per entry; live 6-digit code shown in the entry row, updated every second; click the clock button to copy
- Import OTP secrets from Google Authenticator (`otpauth://` / `otpauth-migration://` URI, or QR image via `pyzbar`) in **Settings → Data**
- **Auto-login (Windows)** — configurable delay per entry; injects `username → TAB → password` keystrokes after opening the URL
- URL shown as inline link icon next to entry name instead of a separate line

### Changed
- Passwords and OTP secrets now share a single Windows Credential Manager entry per vault item (`{"p": "…", "o": "…"}`), halving credential count vs v1.2
- Export/Import now includes OTP secrets in the encrypted `.sesame` file
- Focus border on inputs changed to white (`#e8eaed`)
- Scrollbar always reserves space so buttons are never hidden underneath it

### Fixed
- Removed pre-v1.2 migration code; fixed vault-wipe bug triggered when a single entry failed to parse

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
