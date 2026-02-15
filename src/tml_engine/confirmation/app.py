"""Main Textual application for the confirmation surface.

The CoherenceApp orchestrates the screen flow:
Welcome → Archetype → Domains → Capabilities → Skills → Policies → Edges → Flows → Summary
"""

from __future__ import annotations

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

    def __init__(self, declaration: Declaration, **kwargs) -> None:
        super().__init__(**kwargs)
        self.declaration = declaration

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


def run_confirmation(declaration: Declaration | None = None) -> None:
    """Launch the confirmation surface.

    If no declaration is provided, uses mock data for development/testing.
    """
    if declaration is None:
        from tml_engine.confirmation.mock_data import build_mock_declaration
        declaration = build_mock_declaration()

    app = CoherenceApp(declaration=declaration)
    app.run()


if __name__ == "__main__":
    run_confirmation()
