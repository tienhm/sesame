# Changelog

## v1.6 — 2026-08-01

### Added
- **Browser extension "Sesame Pass" (Chrome, Edge, Firefox, Brave)** — auto-fills username/password into web login forms from the Sesame vault. Double-click a field to see matching entries; each shows one guessed button (👤 for text/email/tel fields, 🔑 for password fields), hold Shift to swap to the other button. Multi-account sites show the stored username below the entry name so you can pick the right account. Connects to the running Sesame app via Chrome/Firefox Native Messaging — no pairing code, no per-site permission prompt; trust is established once via a fixed extension ID allow-listed in the native-messaging host registration. Settings → Extensions tab lists detected browsers with live connected/disconnected status
- **Extension toolbar icon reflects connection state** — colored while the background worker's heartbeat gets a response from Sesame, grayed out otherwise; default icon is gray so a browser that just started (before the first heartbeat) correctly shows "disconnected" rather than a misleading colored icon
- **Native host (`szm_door.exe`) bundled inside `Sesame.exe`** — the bridge process Chrome/Edge/Firefox spawn for each native-messaging session is now embedded in the main exe and auto-deployed to `%LOCALAPPDATA%\Sesame\` on first run; users distribute one file instead of two, and the native host is always kept in sync with the app version
- **Firefox MV3 support** — separate `manifest-ff.json` uses `background.scripts` (event page) instead of `service_worker`, adds `browser_specific_settings.gecko.id` for a stable add-on ID, and declares `data_collection_permissions`; native-messaging registration writes a separate Firefox-format manifest (`allowed_extensions`) and registry key under `HKCU\Software\Mozilla\NativeMessagingHosts`
- **Extension packaging scripts** — `emake.ps1` produces `sesame-pass-chrome-vX.Y.zip`, `sesame-pass-edge-vX.Y.zip`, `sesame-pass-firefox-vX.Y.xpi`, and a `firefox-dev\` unpacked folder for `about:debugging`; version read from `main.py` automatically; `"key"` field stripped from all packages (Chrome Web Store rejects it); zip entries use forward slashes (Firefox rejects backslashes)
- **Movement reminder motivational quotes from file** — `%APPDATA%\Sesame\fun_quotes.txt` (one quote per line) is read at runtime; ships with 30 Vietnamese humorous prompts; users can edit the file to add their own without rebuilding

### Removed
- **Auto-login (Windows)** — the blind `SendInput` keystroke-typing feature (`username → TAB → password` after opening a URL) has been removed in favor of the browser extension's field-targeted autofill, which is strictly more reliable

### Changed
- **Browser extension: double-click instead of focus** — autofill tooltip appears on double-click rather than focus, to avoid competing with the browser's own native password-manager popup (which still reacts to focus)
- **Browser extension: Shift swaps the proposed field** — while the tooltip is open, holding Shift hides the primary button and reveals the alternative (👤 ↔ 🔑), letting you fill the field the heuristic got wrong without Sesame needing to remember anything between visits; replaces the old per-site field-mapping cache
- **Extension popup** — title shows detected browser name ("Sesame Chrome Pass", "Sesame Firefox Pass", etc.); status shows a green/red dot with "Connected" or "Disconnected - Launch Sesame"; browser auto-detected from UA + `navigator.brave.isBrave()`; no manual browser selector
- **Native-messaging registration registers both dev-mode and Web Store extension IDs** — Chrome computes a different ID when the `"key"` field is absent (store uploads strip it), so both are listed in `allowed_origins` to avoid one install path going dark after publish

### Fixed
- **Brave misidentified as Chrome** — Brave deliberately reports a plain Chrome UA; now detected via `navigator.brave.isBrave()`
- **Console spam when Sesame isn't running** — every failed `connectNative()` attempt logged an unread `chrome.runtime.lastError`; now explicitly swallowed
- **Native host crashed on windowed PyInstaller build** — `console=False` leaves `sys.stdin`/`sys.stdout` as `None`; fixed by opening Win32 STD handles directly via `GetStdHandle` + `msvcrt.open_osfhandle`
- **Pipe security hardening silently disabled itself** — `win32security` was imported dynamically inside `_pipe_security_attributes()` so PyInstaller didn't bundle it; the `ImportError` was caught and silently fell back to the default (permissive) DACL; fixed by adding `win32security` to `hiddenimports` in `sesame.spec`
- **Build could fail on a fresh clone** — `resources/icon.png`/`resources/check.svg` were not in `.gitignore`; both are now ignored explicitly

### Security
- **Extension bridge named pipe locked down to the current user** — `ExtensionServer`'s named pipe previously used `CreateNamedPipe`'s default DACL, which allowed any process running as the same Windows user to connect directly and query/reveal vault secrets; the pipe now gets an explicit DACL restricting access to the current user (+ SYSTEM)
- **Extension `reveal` requests scoped to the requesting domain** — entry IDs are small sequential integers; the pipe server now validates the request domain against the entry's saved URL before returning a secret, preventing cross-domain enumeration via direct pipe access

## v1.5 — 2026-07-30

### Added
- **Bitwarden import** — import from an unencrypted Bitwarden JSON export (Settings → Data → Import → Bitwarden tab); only login items are imported; folders become categories; TOTP secrets are preserved; deduplication by URL + username + password skips entries already in the vault
- **Tray menu: Movement Reminder toggle** — enable or disable the movement reminder directly from the system tray without opening Settings
- **Import section redesigned as tabs** — Settings → Data → Import now has three tabs: **Vault** (`.sesame`), **OTP**, **Bitwarden**

### Changed
- **URL normalization** — `http://`/`https://` is stripped when saving an entry; `https://` is re-added automatically when opening the URL in the browser or showing the tooltip; the URL field placeholder now reads `e.g. github.com`

### Fixed
- **Hibernate while blinking** — when the movement reminder was actively blinking and the machine hibernated, the bubble kept blinking after resume even though the countdown had reset; blink and countdown now reset together
- **Auto-start with versioned filename** — `ensure_startup_enabled()` previously checked only whether the registry key existed, not whether the stored path matched the current executable; upgrading from `Sesame-v1.4.exe` to `Sesame-v1.5.exe` left the old path registered and autostart silently stopped working; now re-registers whenever the path changes
- **Checkbox checkmark invisible** — custom QSS overrode the checkbox indicator colour but provided no checkmark image; added `check.svg` and patched the stylesheet loader to resolve resource paths correctly in both dev and PyInstaller modes

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
