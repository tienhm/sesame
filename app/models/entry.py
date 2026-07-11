"""Entry dataclass — represents a single secret/password record."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Entry:
    name: str
    username: str
    category: str
    tags: list[str] = field(default_factory=list)
    url: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

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

        return cls(
            id=data["id"],
            name=data["name"],
            username=data.get("username", ""),
            category=category,
            tags=tags,
            url=data.get("url", ""),
        )

    @staticmethod
    def parse_tags(raw: str) -> list[str]:
        """Split comma-separated tag string, strip whitespace, drop empties."""
        return [t for t in (t.strip() for t in raw.split(",")) if t]
