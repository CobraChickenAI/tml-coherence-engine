"""Pluggable identity provider interface.

Identity providers resolve email addresses to HumanIdentity instances.
Google Workspace, Okta, Microsoft 365, etc. would each implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tml_engine.models.identity import HumanIdentity


class IdentityProvider(ABC):
    """Abstract interface for resolving human identities."""

    @abstractmethod
    async def resolve(self, email: str) -> HumanIdentity:
        """Resolve an email address to a HumanIdentity.

        Must always return a HumanIdentity — implementations should create
        a minimal identity from the email if no richer data is available.
        """

    @abstractmethod
    async def list_available(self) -> list[HumanIdentity]:
        """List all identities known to this provider."""
