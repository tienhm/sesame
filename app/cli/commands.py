"""CLI commands for Sesame."""

from __future__ import annotations

import sys
import time
from typing import Optional

import click

from app.models.vault import Vault
from app.models.entry import Entry
from app.utils.lock_manager import LockManager
from app.config import AppConfig


def _copy_to_clipboard(text: str) -> None:
    """Copy text to system clipboard (cross-platform)."""
    try:
        import pyperclip
        pyperclip.copy(text)
    except ImportError:
        # Fallback: try platform-specific methods
        if sys.platform == "win32":
            import subprocess
            process = subprocess.Popen(
                ["clip"],
                stdin=subprocess.PIPE,
                close_fds=True,
            )
            process.communicate(text.encode("utf-8"))
        elif sys.platform == "darwin":
            import subprocess
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                close_fds=True,
            )
            process.communicate(text.encode("utf-8"))
        else:  # Linux
            import subprocess
            try:
                process = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    close_fds=True,
                )
                process.communicate(text.encode("utf-8"))
            except FileNotFoundError:
                # xclip not available, try xsel
                process = subprocess.Popen(
                    ["xsel", "--clipboard", "--input"],
                    stdin=subprocess.PIPE,
                    close_fds=True,
                )
                process.communicate(text.encode("utf-8"))


class CredentialWizard:
    """Interactive wizard to select and copy credentials."""

    def __init__(self, vault: Vault, lock_mgr: LockManager):
        self._vault = vault
        self._lock_mgr = lock_mgr

    def select_credential(self, entries: list[Entry]) -> Optional[Entry]:
        """Display entries and let user select one with live search.
        
        Returns the selected Entry or None if cancelled.
        """
        if not entries:
            click.echo("❌ No credentials found matching your filters.", err=True)
            return None

        if len(entries) == 1:
            click.echo(f"✓ Found 1 credential: {entries[0].name}")
            return entries[0]

        # Use inquirer for interactive selection with live search
        try:
            import inquirer
        except ImportError:
            # Fallback to simple numbered selection if inquirer not available
            return self._select_credential_simple(entries)

        # Build choices with formatted display
        choices = []
        for entry in entries:
            tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            username_str = f" ({entry.username})" if entry.username else ""
            display = f"{entry.name}{username_str}{tags_str}"
            choices.append((display, entry))

        # Create inquirer question with live search
        questions = [
            inquirer.List(
                "credential",
                message="Select credential (use ↑↓ arrows, type to search, Enter to select)",
                choices=[c[0] for c in choices],
                carousel=True,
            )
        ]

        try:
            answers = inquirer.prompt(questions)
            if answers is None:
                return None
            
            selected_display = answers["credential"]
            for display, entry in choices:
                if display == selected_display:
                    return entry
        except (KeyboardInterrupt, EOFError):
            return None

    def _select_credential_simple(self, entries: list[Entry]) -> Optional[Entry]:
        """Fallback: simple numbered selection without live search."""
        click.echo(f"\n📋 Found {len(entries)} credentials:\n")
        for i, entry in enumerate(entries, 1):
            tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            username_str = f" ({entry.username})" if entry.username else ""
            click.echo(f"  {i}. {entry.name}{username_str}{tags_str}")

        click.echo()
        while True:
            try:
                choice = click.prompt(
                    "Select credential (number)",
                    type=int,
                    default=1,
                )
                if 1 <= choice <= len(entries):
                    return entries[choice - 1]
                click.echo(f"❌ Please enter a number between 1 and {len(entries)}.")
            except click.Abort:
                return None

    def copy_credential(self, entry: Entry, copy_username: bool = False) -> None:
        """Copy username or password to clipboard with countdown."""
        secret = self._vault.get_secret(entry.id)
        
        if copy_username:
            if not entry.username:
                click.echo("❌ No username set for this credential.", err=True)
                return
            _copy_to_clipboard(entry.username)
            click.echo(f"✓ Username copied: {entry.username}")
        else:
            # Copy password with countdown
            _copy_to_clipboard(secret)
            click.echo(f"✓ Password copied to clipboard")
            self._show_countdown(30)

    def _show_countdown(self, seconds: int) -> None:
        """Display countdown timer in console."""
        for remaining in range(seconds, 0, -1):
            click.echo(f"\r⏱️  Clearing clipboard in {remaining}s...", nl=False)
            sys.stdout.flush()
            time.sleep(1)
        # Clear clipboard
        _copy_to_clipboard("")
        click.echo("\r✓ Clipboard cleared.                    ")

    def select_tags(self, entries: list[Entry]) -> Optional[tuple[str, ...]]:
        """Interactive tag selection with live search.
        
        Returns tuple of selected tags or None if cancelled.
        """
        if not entries:
            return ()

        # Collect all unique tags from entries
        all_tags = set()
        for entry in entries:
            all_tags.update(t.lower() for t in entry.tags)

        if not all_tags:
            click.echo("ℹ️  No tags available. Showing all credentials.")
            return ()

        all_tags_sorted = sorted(all_tags)

        # Use inquirer for interactive tag selection with live search
        try:
            import inquirer
        except ImportError:
            # Fallback: simple tag input
            return self._select_tags_simple()

        # Create inquirer question with checkbox for multiple selection
        questions = [
            inquirer.Checkbox(
                "tags",
                message="Select tags (use ↑↓ arrows, Space to toggle, Enter to confirm)",
                choices=all_tags_sorted,
                carousel=True,
            )
        ]

        try:
            answers = inquirer.prompt(questions)
            if answers is None:
                return None
            return tuple(answers["tags"])
        except (KeyboardInterrupt, EOFError):
            return None

    def _select_tags_simple(self) -> Optional[tuple[str, ...]]:
        """Fallback: simple comma-separated tag input."""
        tag_input = click.prompt(
            "Enter tags (comma-separated, or press Enter to skip)",
            default="",
        )
        if not tag_input:
            return ()
        return tuple(Entry.parse_tags(tag_input))


@click.group()
def cli():
    """Sesame CLI - Lightweight password manager for Windows & Linux."""
    pass


@cli.command()
@click.argument("tags", nargs=-1, required=False)
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--username", "-u", is_flag=True, help="Copy username instead of password")
@click.option("--show", "-s", is_flag=True, help="Show password instead of copying")
def get(tags: tuple[str, ...], category: Optional[str], username: bool, show: bool) -> None:
    """Get and copy credentials by tags.
    
    Examples:
        sesame get                    # Interactive tag search + credential selection
        sesame get gmail              # Filter by tag 'gmail'
        sesame get gmail work         # Filter by tags 'gmail' AND 'work'
        sesame get -c Work            # Filter by category 'Work'
        sesame get gmail -u           # Copy username instead
        sesame get gmail -s           # Show password in console (no copy)
    """
    vault = Vault()
    config = AppConfig()
    lock_mgr = LockManager(config)
    wizard = CredentialWizard(vault, lock_mgr)

    # Filter entries
    entries = vault.entries

    # Filter by category
    if category:
        entries = [e for e in entries if e.category.lower() == category.lower()]

    # If no tags provided, offer interactive tag selection
    if not tags:
        selected_tags = wizard.select_tags(entries)
        if selected_tags is None:
            return
        tags = selected_tags

    # Filter by tags (AND logic)
    if tags:
        tag_set = set(t.lower() for t in tags)
        entries = [
            e for e in entries
            if tag_set.issubset(set(t.lower() for t in e.tags))
        ]

    # Select credential
    selected = wizard.select_credential(entries)
    if not selected:
        return

    # Check master password lock
    if lock_mgr.is_locked(selected.category):
        if not lock_mgr.unlock(selected.category):
            click.echo("❌ Master password incorrect or cancelled.", err=True)
            return

    # Display entry details
    click.echo(f"\n📝 {selected.name}")
    if selected.username:
        click.echo(f"   Username: {selected.username}")
    if selected.url:
        click.echo(f"   URL: {selected.url}")
    if selected.tags:
        click.echo(f"   Tags: {', '.join(selected.tags)}")
    click.echo()

    # Copy or show
    if show:
        secret = vault.get_secret(selected.id)
        click.echo(f"   Secret: {secret}")
    else:
        # Prompt what to copy
        if selected.username and not username:
            choice = click.prompt(
                "Copy [p]assword or [u]sername?",
                type=click.Choice(["p", "u"], case_sensitive=False),
                default="p",
            )
            username = choice.lower() == "u"

        wizard.copy_credential(selected, copy_username=username)


@cli.command()
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--tag", "-t", multiple=True, help="Filter by tag (can use multiple times)")
@click.option("--json", is_flag=True, help="Output as JSON")
def list(category: Optional[str], tag: tuple[str, ...], json: bool) -> None:
    """List all credentials.
    
    Examples:
        sesame list                   # List all
        sesame list -c Work           # Filter by category
        sesame list -t gmail -t work  # Filter by tags (AND logic)
        sesame list --json            # Output as JSON
    """
    vault = Vault()
    entries = vault.entries

    # Filter by category
    if category:
        entries = [e for e in entries if e.category.lower() == category.lower()]

    # Filter by tags (AND logic)
    if tag:
        tag_set = set(t.lower() for t in tag)
        entries = [
            e for e in entries
            if tag_set.issubset(set(t.lower() for t in e.tags))
        ]

    if not entries:
        click.echo("No credentials found.")
        return

    if json:
        import json as json_module
        data = [e.to_dict() for e in entries]
        click.echo(json_module.dumps(data, indent=2))
    else:
        # Table format
        click.echo(f"\n📋 {len(entries)} credential(s):\n")
        for entry in entries:
            tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            username_str = f" ({entry.username})" if entry.username else ""
            click.echo(f"  • {entry.name}{username_str}{tags_str}")
            click.echo(f"    Category: {entry.category}")
            if entry.url:
                click.echo(f"    URL: {entry.url}")
            click.echo()


@cli.command()
@click.option("--name", "-n", prompt=True, help="Credential name")
@click.option("--username", "-u", default="", help="Username")
@click.option("--secret", "-s", prompt=True, hide_input=True, confirmation_prompt=True, help="Password/secret")
@click.option("--url", default="", help="URL")
@click.option("--category", "-c", default="General", help="Category")
@click.option("--tags", "-t", default="", help="Tags (comma-separated)")
def add(name: str, username: str, secret: str, url: str, category: str, tags: str) -> None:
    """Add a new credential.
    
    Examples:
        sesame add -n Gmail -u user@gmail.com -c Email -t google,email
    """
    from app.models.entry import Entry
    
    vault = Vault()
    
    # Parse tags
    tag_list = Entry.parse_tags(tags) if tags else []
    
    # Create entry
    entry = Entry(
        name=name,
        username=username,
        category=category,
        tags=tag_list,
        url=url,
    )
    
    # Save
    vault.add_entry(entry, secret)
    click.echo(f"✓ Credential '{name}' added to category '{category}'")


@cli.command()
@click.argument("entry_id")
def delete(entry_id: str) -> None:
    """Delete a credential by ID."""
    vault = Vault()
    
    # Find entry
    entry = next((e for e in vault.entries if e.id == entry_id or e.name.lower() == entry_id.lower()), None)
    if not entry:
        click.echo(f"❌ Credential '{entry_id}' not found.", err=True)
        return
    
    if click.confirm(f"Delete '{entry.name}'?"):
        vault.delete_entry(entry.id)
        click.echo(f"✓ Credential '{entry.name}' deleted")
    else:
        click.echo("Cancelled.")


@cli.command()
@click.option("--length", "-l", default=16, type=int, help="Password length (4-64)")
@click.option("--letters", is_flag=True, default=True, help="Include letters")
@click.option("--digits", is_flag=True, default=True, help="Include digits")
@click.option("--special", is_flag=True, default=False, help="Include special characters")
def generate(length: int, letters: bool, digits: bool, special: bool) -> None:
    """Generate a random password."""
    import secrets
    import string
    
    if length < 4 or length > 64:
        click.echo("❌ Length must be between 4 and 64.", err=True)
        return
    
    chars = ""
    if letters:
        chars += string.ascii_letters
    if digits:
        chars += string.digits
    if special:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    if not chars:
        click.echo("❌ Select at least one character type.", err=True)
        return
    
    password = "".join(secrets.choice(chars) for _ in range(length))
    click.echo(f"🔐 Generated password: {password}")


@cli.command()
@click.option("--output", "-o", required=True, help="Output file path")
@click.option("--password", "-p", prompt=True, hide_input=True, confirmation_prompt=True, help="Export password")
def export(output: str, password: str) -> None:
    """Export vault to encrypted .sesame file."""
    from app.utils.vault_io import export_vault
    
    vault = Vault()
    try:
        export_vault(vault, output, password)
        click.echo(f"✓ Vault exported to {output}")
    except Exception as e:
        click.echo(f"❌ Export failed: {e}", err=True)


@cli.command()
@click.argument("file_path")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Import password")
def import_vault(file_path: str, password: str) -> None:
    """Import credentials from encrypted .sesame file."""
    from app.utils.vault_io import import_vault as import_vault_func
    
    vault = Vault()
    try:
        import_vault_func(vault, file_path, password)
        click.echo(f"✓ Vault imported from {file_path}")
    except Exception as e:
        click.echo(f"❌ Import failed: {e}", err=True)


if __name__ == "__main__":
    cli()
