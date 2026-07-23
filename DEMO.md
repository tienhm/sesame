# Sesame CLI - Demo Walkthrough

## Demo: Getting a credential with interactive wizard

### Step 1: List all credentials
```bash
$ python cli.py list

📋 4 credential(s):

  • Youtube Monitor (admin) [vps, hmt.ovh]
    Category: Private
    URL: https://yt.hmt.ovh

  • Polarion admin uat (admin) [uat, polarion]
    Category: IBA
    URL: https://polarion-uat.goiba.net

  • Silverbullet (hmt) [vps, hmt.ovh]
    Category: Private
    URL: https://notes.hmt.ovh

  • Github (tienhm@github.com) [git]
    Category: Private
    URL: https://github.com
```

### Step 2: Filter by tag and open interactive wizard
```bash
$ python cli.py get vps

📋 Found 2 credentials:

  1. Youtube Monitor (admin) [vps, hmt.ovh]
  2. Silverbullet (hmt) [vps, hmt.ovh]

Select credential (number) [1]: 1
```

### Step 3: View credential details and choose what to copy
```bash
📝 Youtube Monitor
   Username: admin
   URL: https://yt.hmt.ovh
   Tags: vps, hmt.ovh

Copy [p]assword or [u]sername? [p]: p
```

### Step 4: Password copied with countdown
```bash
✓ Password copied to clipboard
⏱️  Clearing clipboard in 30s...
⏱️  Clearing clipboard in 29s...
⏱️  Clearing clipboard in 28s...
...
⏱️  Clearing clipboard in 1s...
✓ Clipboard cleared.
```

---

## Demo: Filter by multiple tags (AND logic)

### Get credentials with BOTH 'vps' AND 'hmt.ovh' tags
```bash
$ python cli.py get vps hmt.ovh

📋 Found 2 credentials:

  1. Youtube Monitor (admin) [vps, hmt.ovh]
  2. Silverbullet (hmt) [vps, hmt.ovh]

Select credential (number) [1]: 2
```

---

## Demo: Filter by category

### Get credentials from 'Private' category
```bash
$ python cli.py get -c Private

📋 Found 3 credentials:

  1. Youtube Monitor (admin) [vps, hmt.ovh]
  2. Silverbullet (hmt) [vps, hmt.ovh]
  3. Github (tienhm@github.com) [git]

Select credential (number) [1]: 3
```

---

## Demo: Copy username instead of password

```bash
$ python cli.py get github -u

✓ Found 1 credential: Github
📝 Github
   Username: tienhm@github.com
   URL: https://github.com
   Tags: git

✓ Username copied: tienhm@github.com
```

---

## Demo: Show password without copying

```bash
$ python cli.py get github -s

✓ Found 1 credential: Github
📝 Github
   Username: tienhm@github.com
   URL: https://github.com
   Tags: git

   Secret: your_password_here
```

---

## Demo: Add new credential

```bash
$ python cli.py add

Name: Gmail
Username: user@gmail.com
Secret: [hidden input]
Confirm Secret: [hidden input]
URL: https://gmail.com
Category [General]: Email
Tags (comma-separated): google,email

✓ Credential 'Gmail' added to category 'Email'
```

---

## Demo: Generate password

```bash
$ python cli.py generate -l 32 --special

🔐 Generated password: aB3$xY9@mK2#pL8&qR5!vW7^tU4*sN6
```

---

## Demo: Export vault

```bash
$ python cli.py export -o backup.sesame

Export password: [hidden input]
Confirm Export password: [hidden input]

✓ Vault exported to backup.sesame
```

---

## Demo: Import vault

```bash
$ python cli.py import backup.sesame

Import password: [hidden input]

✓ Vault imported from backup.sesame
```

---

## Demo: List with JSON output

```bash
$ python cli.py list --json

[
  {
    "id": "abc123...",
    "name": "Youtube Monitor",
    "username": "admin",
    "category": "Private",
    "tags": ["vps", "hmt.ovh"],
    "url": "https://yt.hmt.ovh"
  },
  ...
]
```

---

## Key Features Demonstrated

✅ **Interactive wizard** - Select from numbered list  
✅ **Tag filtering** - AND logic for multiple tags  
✅ **Category filtering** - Filter by category  
✅ **30-second countdown** - Auto-clear clipboard  
✅ **Copy username or password** - Choose what to copy  
✅ **Show password** - Display without copying  
✅ **Add credentials** - Interactive form  
✅ **Generate passwords** - Configurable options  
✅ **Export/Import** - Encrypted backup/restore  
✅ **JSON output** - For scripting/automation  
