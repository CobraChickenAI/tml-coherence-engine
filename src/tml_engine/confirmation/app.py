"""Main Textual application for the confirmation surface.

The CoherenceApp orchestrates the screen flow:
Welcome → Archetype → Domains → Capabilities → Skills → Policies → Edges → Flows → Summary
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.app import App

from tml_engine.confirmation.screens.archetype import ArchetypeScreen
from tml_engine.confirmation.screens.capabilities import CapabilitiesScreen
from tml_engine.confirmation.screens.domains import DomainsScreen
from tml_engine.confirmation.screens.edges import EdgesScreen
from tml_engine.confirmation.screens.flows import FlowsScreen
from tml_engine.confirmation.screens.policies import PoliciesScreen
from tml_engine.confirmation.screens.skills import SkillsScreen
from tml_engine.confirmation.screens.summary import SummaryScreen
from tml_engine.confirmation.screens.welcome import WelcomeScreen
from tml_engine.models.declaration import Declaration

if TYPE_CHECKING:
    from tml_engine.models.primitives import ProvenanceEntry
    from tml_engine.storage.sqlite import StorageEngine

logger = logging.getLogger(__name__)


class CoherenceApp(App):
    """TML Coherence Engine — Confirmation Surface.

    Wizard-style flow through all primitive types for human confirmation.
    """

    TITLE = "TML Coherence Engine"
    SUB_TITLE = "Confirmation Surface"

    CSS = """
    Screen {
        background: $background;
    }
    """

    def __init__(
        self,
        declaration: Declaration,
        storage: StorageEngine | None = None,
        identity_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.declaration = declaration
        self.storage = storage
        self.identity_id = identity_id

    def on_mount(self) -> None:
        """Install all screens from the Declaration and show the welcome screen."""
        d = self.declaration

        self.install_screen(
            WelcomeScreen(declaration=d),
            name="welcome",
        )

        if d.archetypes:
            self.install_screen(
                ArchetypeScreen(archetype=d.archetypes[0]),
                name="archetype",
            )

        self.install_screen(
            DomainsScreen(domains=d.domains),
            name="domains",
        )

        self.install_screen(
            CapabilitiesScreen(capabilities=d.capabilities),
            name="capabilities",
        )

        self.install_screen(
            SkillsScreen(capabilities=d.capabilities),
            name="skills",
        )

        self.install_screen(
            PoliciesScreen(policies=d.policies),
            name="policies",
        )

        self.install_screen(
            EdgesScreen(capabilities=d.capabilities),
            name="edges",
        )

        self.install_screen(
            FlowsScreen(connectors=d.connectors, bindings=d.bindings),
            name="flows",
        )

        self.install_screen(
            SummaryScreen(declaration=d),
            name="summary",
        )

        self.push_screen("welcome")

    async def persist_confirmation(
        self,
        *,
        primitive_id: str,
        primitive_type: str,
        scope_id: str,
        status: str,
        actor_email: str,
        provenance_entry: ProvenanceEntry,
    ) -> None:
        """Persist a confirmation action to storage.

        No-op if storage is not configured (mock mode).
        """
        if self.storage is None:
            return
        try:
            await self.storage.update_confirmation(
                primitive_id,
                status=status,
                confirmed_by=actor_email,
            )
            await self.storage.append_provenance(
                provenance_id=provenance_entry.id,
                scope_id=scope_id,
                primitive_id=primitive_id,
                primitive_type=primitive_type,
                action=provenance_entry.action,
                actor_identity_id=self.identity_id or actor_email,
                details=provenance_entry.details,
                previous_state=provenance_entry.previous_state,
            )
        except Exception:
            logger.exception("Failed to persist confirmation for %s", primitive_id)
            self.notify("Storage error — confirmation saved in memory only", severity="warning")

    async def persist_primitive_update(
        self,
        *,
        primitive_id: str,
        primitive_type: str,
        scope_id: str,
        data: dict,
        source: str,
    ) -> None:
        """Persist updated primitive data (for sub-component changes like skills/exceptions)."""
        if self.storage is None:
            return
        try:
            await self.storage.store_primitive(
                primitive_id=primitive_id,
                primitive_type=primitive_type,
                scope_id=scope_id,
                data=data,
                source=source,
            )
        except Exception:
            logger.exception("Failed to persist primitive update for %s", primitive_id)

    async def persist_declaration_snapshot(self) -> None:
        """Persist the final Declaration snapshot to storage."""
        if self.storage is None:
            return
        try:
            self.declaration.compute_completion()
            await self.storage.store_declaration(
                declaration_id=self.declaration.id,
                version=self.declaration.version,
                scope_id=self.declaration.scope.id,
                data=self.declaration.model_dump(mode="json"),
                completion=self.declaration.completion_percentage,
            )
        except Exception:
            logger.exception("Failed to persist Declaration snapshot")
            self.notify("Storage error — Declaration not saved", severity="warning")


def run_confirmation(declaration: Declaration | None = None) -> None:
    """Launch the confirmation surface.

    If no declaration is provided, uses mock data for development/testing.
    """
    if declaration is None:
        from tml_engine.confirmation.mock_data import build_mock_declaration

        declaration = build_mock_declaration()

    app = CoherenceApp(declaration=declaration)
    app.run()


async def run_confirmation_async(
    declaration: Declaration,
    storage: StorageEngine,
    identity_id: str,
) -> None:
    """Launch the confirmation surface with storage persistence."""
    app = CoherenceApp(
        declaration=declaration,
        storage=storage,
        identity_id=identity_id,
    )
    await app.run_async()


if __name__ == "__main__":
    run_confirmation()
