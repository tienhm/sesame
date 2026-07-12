# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅        |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub Issues.**

If you discover a security vulnerability, please report it privately by emailing:

**minhtien.hoang@comexis.net**

Include as much detail as possible:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive a response within **72 hours**. Once the issue is confirmed, a fix will be released as soon as possible.

## Scope

Security issues relevant to this project include:

- Secrets leaking outside Windows Credential Manager (e.g. written to disk, logs, or memory dumps)
- Bypass of the master password protection
- Weaknesses in the export file encryption (AES-256-GCM / PBKDF2)
- Clipboard not being cleared after the 30-second countdown
- Privilege escalation or unauthorized access to vault data

## Out of Scope

- Vulnerabilities requiring physical access to an already unlocked Windows session (Windows DPAPI is the trust boundary)
- Social engineering attacks
- Denial of service against the local application
