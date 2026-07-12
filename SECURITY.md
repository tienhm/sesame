# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅        |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub Issues.**

Use GitHub's private vulnerability reporting instead:

👉 **[Report a vulnerability](https://github.com/tienhm/sesame/security/advisories/new)**

Include as much detail as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within **72 hours**. Once the issue is confirmed, a fix will be released as soon as possible.

## Scope

Security issues relevant to this project include:

- Secrets unintentionally written to disk, logs, or temp files
- Master password UI/logic bypass (e.g. a code path that skips the prompt)
- Clipboard secret not cleared after the 30-second countdown due to a bug
- Export file: incorrect use of AES-256-GCM (e.g. IV reuse, missing authentication tag check)
- Export file: PBKDF2 iteration count or salt handling bug that weakens the derived key

## Out of Scope

- Theoretical breaks of AES-256-GCM or PBKDF2 as algorithms — these are handled by the upstream `cryptography` library
- Vulnerabilities requiring physical access to an already unlocked Windows session (Windows DPAPI is the trust boundary)
- Social engineering attacks
- Denial of service against the local application
