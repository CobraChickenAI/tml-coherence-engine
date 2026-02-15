"""Declaration — the versioned, validated, diffable root of trust."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from tml_engine.models.identity import ConfirmationStatus
from tml_engine.models.primitives import (
    Archetype,
    Binding,
    Capability,
    Connector,
    Domain,
    Policy,
    ProvenanceEntry,
    Scope,
    View,
)


class Declaration(BaseModel):
    """The complete confirmed architecture for one or more humans within a Scope.
    This is what gets exported, what agents resolve against, what the organization acts on."""

    id: str
    version: str
    scope: Scope
    archetypes: list[Archetype]
    domains: list[Domain]
    capabilities: list[Capability]
    views: list[View]
    policies: list[Policy]
    connectors: list[Connector]
    bindings: list[Binding]
    provenance: list[ProvenanceEntry]
    created_at: datetime
    last_confirmed_at: datetime | None = None
    completion_percentage: float = 0.0

    def _confirmable_primitives(self) -> list:
        """Return all primitives that have a confirmation field."""
        primitives: list = []
        primitives.append(self.scope)
        primitives.extend(self.archetypes)
        primitives.extend(self.domains)
        primitives.extend(self.capabilities)
        primitives.extend(self.policies)
        primitives.extend(self.connectors)
        primitives.extend(self.bindings)
        return primitives

    def confirmed_count(self) -> int:
        """Count of all primitives with confirmed or corrected status."""
        count = 0
        for p in self._confirmable_primitives():
            if p.confirmation and p.confirmation.status in (
                ConfirmationStatus.CONFIRMED,
                ConfirmationStatus.CORRECTED,
            ):
                count += 1
        return count

    def unconfirmed_count(self) -> int:
        """Count of primitives still awaiting confirmation."""
        count = 0
        for p in self._confirmable_primitives():
            if not p.confirmation or p.confirmation.status == ConfirmationStatus.UNCONFIRMED:
                count += 1
        return count

    def total_confirmable(self) -> int:
        """Total number of confirmable primitives."""
        return len(self._confirmable_primitives())

    def compute_completion(self) -> float:
        """Recompute and return completion percentage."""
        total = self.total_confirmable()
        if total == 0:
            return 0.0
        self.completion_percentage = (self.confirmed_count() / total) * 100.0
        return self.completion_percentage
