"""Entry dataclass — represents a single secret/password record."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Entry:
    name: str
    username: str
    category: str
    tags: list[str] = field(default_factory=list)
    url: str = ""
    auto_login_ms: int = 0  # 0/absent = disabled; else ms to wait after opening url before sending keys
    id: str = ""  # assigned by Vault.add_entry — short, reused-gap int as str

    # ------------------------------------------------------------------
    # Serialisation helpers (secret is NOT stored here — lives in keyring)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "category": self.category,
            "tags": self.tags,
            "url": self.url,
            "auto_login_ms": self.auto_login_ms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entry":
        raw_tags = data.get("tags", [])
        tags = [t for raw in raw_tags for t in Entry.parse_tags(raw)]

        category = data.get("category", "General") or "General"

        # Migrate legacy data: category stored as comma-separated values
        if "," in category and not tags:
            tags = Entry.parse_tags(category)
            category = "General"

        try:
            auto_login_ms = max(0, int(data.get("auto_login_ms") or 0))
        except (TypeError, ValueError):
            auto_login_ms = 0

        return cls(
            id=data["id"],
            name=data["name"],
            username=data.get("username", ""),
            category=category,
            tags=tags,
            url=data.get("url", ""),
            auto_login_ms=auto_login_ms,
        )

    @staticmethod
    def parse_tags(raw: str) -> list[str]:
        """Split comma-separated tag string, strip whitespace, drop empties."""
        return [t for t in (t.strip() for t in raw.split(",")) if t]
