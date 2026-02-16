"""Local identity provider backed by SQLite storage.

This is the default provider — resolves identities from the local database,
creating minimal identities when no stored record exists.
"""

from __future__ import annotations

from tml_engine.identity.base import IdentityProvider
from tml_engine.models.identity import HumanIdentity
from tml_engine.storage.sqlite import StorageEngine


class LocalIdentityProvider(IdentityProvider):
    """Resolves identities from the local SQLite database."""

    def __init__(self, storage: StorageEngine) -> None:
        self._storage = storage

    async def resolve(self, email: str) -> HumanIdentity:
        row = await self._storage.get_identity_by_email(email)
        if row:
            return HumanIdentity(
                email=row["email"],
                display_name=row["display_name"],
                title=row.get("title"),
                department=row.get("department"),
                workspace_id=row.get("workspace_id"),
            )
        # Create minimal identity from email
        local_part = email.split("@")[0]
        display_name = local_part.replace(".", " ").replace("_", " ").title()
        return HumanIdentity(email=email, display_name=display_name)

    async def list_available(self) -> list[HumanIdentity]:
        cursor = await self._storage.db.execute("SELECT * FROM identities ORDER BY display_name")
        rows = await cursor.fetchall()
        return [
            HumanIdentity(
                email=row["email"],
                display_name=row["display_name"],
                title=row["title"],
                department=row["department"],
                workspace_id=row["workspace_id"],
            )
            for row in rows
        ]
