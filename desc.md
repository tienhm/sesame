## Sesame v1.3

> **Se**crets **Sa**fe **Me**moriser

A lightweight Windows 64-bit desktop password manager. Stores secrets in Windows Credential Manager (DPAPI-encrypted). No installation required, no admin rights needed.

---

### What's new in v1.3

**TOTP / OTP support**
Store a base32 TOTP secret per entry. The live 6-digit code is displayed in the entry row, updated every second with a remaining-time counter. Click the clock button to copy the current code to clipboard.

Import OTP secrets from Google Authenticator:
- Paste an `otpauth://` or `otpauth-migration://` URI directly in **Settings → Data**
- Or browse a QR-code image file (requires `pyzbar`)
- Matching by service name + account — updates existing entries or creates new ones

**Compact credential storage**
Passwords and OTP secrets are now stored together in a single Windows Credential Manager entry per vault item (`{"p": "…", "o": "…"}`), halving the number of credentials compared to v1.2.

**Auto-login (Windows)**
Set a delay (ms) per entry. After clicking the URL, Sesame waits then injects `username → TAB → password` as keystrokes into the focused window. No trailing Enter — you verify focus before submitting.

**URL as inline link icon**
The URL is now shown as a small link icon (⛓) inline with the entry name rather than as a separate text line.

**OTP colour**
The OTP code label uses a bright, easy-to-read colour (`#a5b4fc`) distinct from the entry name.

---

### Also in v1.3

- Export / Import (Settings → Data tab) now includes OTP secrets in the encrypted `.sesame` file
- Focus border on inputs changed to white (`#e8eaed`) for consistency
- Scrollbar always reserves space — buttons no longer hidden under the scrollbar
- Code review: removed all pre-v1.2 migration code; fixed vault-wipe bug when one entry fails to parse; dead code cleanup

---

### Download

**Download zip (recommended):** `sesame-binary-w64.zip` — Password: `sesame`
**Download exe directly:** `Sesame.exe`

> ⚠️ Some antivirus engines may flag this exe — this is a **false positive** common with PyInstaller-packaged Python apps. The source code is fully open on this repository. If in doubt, build from source.
