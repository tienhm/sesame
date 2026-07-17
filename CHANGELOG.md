# Changelog

## v1.2 — 2026-07-17

### Changed
- **Secret storage optimized** — secrets now written directly via `pywin32` (`win32cred`) instead of through `keyring`, with an explicit compact layout: `TargetName` = `SZM:<entry-id>`, `UserName` = "" (the account username lives only in `sesame_vault.json`, no longer duplicated into Credential Manager).
- Entry ids are now short integers assigned locally by the vault (reusing gaps left by deletions) instead of global UUIDs, shrinking each Credential Manager entry.
- Secrets written by older versions are migrated to the new layout automatically the first time they're read; nothing to do manually.
- Double-clicking the system tray icon now calls *Locate Sesame* (flashes the bubble at screen centre) instead of toggling the bubble.

## v1.1 — 2026-07-17

### Fixed
- **Vault index moved from Windows Credential Manager to file** (`%APPDATA%\Sesame\sesame_vault.json`) — resolves silent save failures on corporate machines where Credential Manager enforces a 2 560-byte per-credential limit. Existing data is migrated automatically on first launch; no manual action required.
- Security review fixes:
  - `remove_lock` typo → `remove_locked_category` (crash on category delete)
  - `itemChanged` signal accumulated duplicate connections on each Security tab refresh (corrupted lock state)
  - Sponsor button in toolbar was never connected to a slot
  - PBKDF2 iterations for master password raised from 100 000 to 600 000 (matches export/import)
  - Clipboard `clear()` now uses the Win32 path so the empty write also carries `ExcludeClipboardContentFromMonitorProcessing`
  - Unclosed file handle in vault import path
  - `config.get("key") or default` falsy-zero bug (offset = 0 was treated as 0.5)
  - `random.choice` → `secrets.choice` for password generator (cryptographically secure)
  - `countdown = active_entry_id and None` always evaluated to `None` — countdown badge now shown correctly on list rebuild

### Changed
- Tag list is now **single-select** — click a tag to filter, click again to deselect
- Selected tag / entry background is **30% more opaque** than the component opacity setting for clear visual feedback

### Added
- **Drag-to-reorder entries** — drag an entry row up or down; new order is saved immediately
- Viewport preview in Settings now correctly maps to the panel's actual render region (scale-aware coordinate conversion)
- Bubble countdown mirror when panel is closed (already in v1.0 but now also applies immediately on restore)

---

## v1.0 — 2026-07-12

Initial release.

- Floating always-on-top bubble with drag positioning
- Vault panel: search, category filter, tag filter, entry list
- Entry fields: name, username, URL, secret, tags, category
- Inline copy (👤 username, 🔑 password with 30 s auto-clear), edit (✏), password generator (🎲)
- Clipboard excluded from Windows Clipboard History (Win+V)
- Master password protection per category (PBKDF2-HMAC-SHA256, 600 000 iterations)
- Export / Import vault (AES-256-GCM, PBKDF2-HMAC-SHA256, 600 000 iterations, random salt)
- Background image support with drag-to-position viewport and component opacity slider
- Single instance enforcement with bubble flash-and-center
- Font Awesome 6 icons
- Start with Windows (no admin rights required)
