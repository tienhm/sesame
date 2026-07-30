# Sesame v1.5 — Release Notes

**Release date:** 2026-07-30

---

## What's new

### Bitwarden import

You can now import your passwords directly from Bitwarden without any third-party tool.

1. In Bitwarden, go to **Tools → Export Vault** and choose **JSON** format with **No encryption**.
2. In Sesame, open **Settings → Data → Import → Bitwarden** tab.
3. Browse to the exported `.json` file and click **Import from Bitwarden…**.

Only **login items** are imported. Notes, cards, and identities are skipped. Bitwarden folders become Sesame categories. TOTP secrets are carried over automatically.

**Duplicate detection:** entries where URL + username + password all match an existing vault entry are skipped, so re-importing after adding new accounts is safe.

### Movement Reminder toggle in the tray menu

The system tray context menu now has a **Movement Reminder** checkbox. Enable or disable the reminder with a single click — no need to open Settings.

### Tabbed Import section

Settings → Data → Import section has been reorganised into three tabs:

| Tab | What it imports |
|---|---|
| **Vault** | Encrypted `.sesame` backup (requires password) |
| **OTP** | `otpauth://` / `otpauth-migration://` URI or QR image |
| **Bitwarden** | Unencrypted Bitwarden JSON export |

---

## Changes

### URL normalization

URLs are now stored without a protocol prefix. When you type or paste `https://github.com`, Sesame stores `github.com` and re-adds `https://` when opening the link in the browser. The URL field placeholder is updated to `e.g. github.com` to reflect this.

---

## Fixed

### Hibernate while blinking
When the movement reminder timer elapsed and the bubble was blinking, putting the machine to sleep and waking it up reset the countdown timer but left the bubble blinking. The blink and countdown now reset together on resume.

### Auto-start broken after upgrading to a new version
The startup registry key (`HKCU\...\Run\Sesame`) stored the path to the previous executable. After upgrading from `Sesame-v1.4.exe` to `Sesame-v1.5.exe`, the old path remained registered and Windows could not find the file at boot, so Sesame never launched automatically. Sesame now detects the mismatch and re-registers the correct path on first run.

### Checkbox checkmark invisible
The custom dark theme overrode the checkbox indicator background colour but removed the built-in checkmark. Checked checkboxes now show a white ✓ on the purple background.

---

## Files

- `Sesame-v1.5.exe` — single-file Windows executable, no installation required.
- Source: `main.py` + `app/` package, run inside `.venv`.

---

## Upgrade notes

- Existing vault data, config, and cache are fully compatible — no migration needed.
- If **Start with Windows** was enabled with a previous version, Sesame will automatically update the registry key to point to `Sesame-v1.5.exe` on first launch.
