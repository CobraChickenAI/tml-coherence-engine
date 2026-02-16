"""WelcomeScreen — establishes Scope and Archetype identity."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.models.declaration import Declaration


class WelcomeScreen(Screen):
    """First screen: shows who is being confirmed and the scope of the Declaration."""

    DEFAULT_CSS = """
    WelcomeScreen Horizontal {
        height: 1fr;
    }

    WelcomeScreen .main-content {
        width: 1fr;
        height: 1fr;
        padding: 2 4;
    }

    WelcomeScreen .welcome-title {
        text-style: bold;
        text-align: center;
        padding: 1 0 2 0;
        color: $primary;
    }

    WelcomeScreen .identity-panel {
        padding: 1 2;
        margin: 1 0;
        border: round $primary;
        background: $surface;
        height: auto;
    }

    WelcomeScreen .scope-panel {
        padding: 1 2;
        margin: 1 0;
        border: round $secondary;
        background: $surface;
        height: auto;
    }

    WelcomeScreen .panel-heading {
        text-style: bold;
        padding: 0 0 1 0;
    }

    WelcomeScreen .detail-line {
        padding: 0 1;
    }

    WelcomeScreen .onboarding-panel {
        padding: 1 2;
        margin: 1 0;
        border: round $warning;
        background: $surface;
        height: auto;
    }

    WelcomeScreen .begin-button {
        margin: 2 0;
        align: center middle;
    }

    WelcomeScreen Button {
        min-width: 30;
    }
    """

    BINDINGS = [
        ("enter", "begin", "Begin Confirmation"),
        ("q", "app.quit", "Quit"),
    ]

    def __init__(self, declaration: Declaration, **kwargs) -> None:
        super().__init__(**kwargs)
        self.declaration = declaration

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with VerticalScroll(classes="main-content"):
                yield Static(
                    "TML Coherence Engine — Confirmation Surface",
                    classes="welcome-title",
                )

                d = self.declaration
                identity = d.scope.owner_identity

                with Vertical(classes="identity-panel"):
                    yield Label("Who You Are", classes="panel-heading")
                    yield Label(f"  Name:       {identity.display_name}", classes="detail-line")
                    yield Label(f"  Email:      {identity.email}", classes="detail-line")
                    if identity.title:
                        yield Label(f"  Title:      {identity.title}", classes="detail-line")
                    if identity.department:
                        yield Label(f"  Department: {identity.department}", classes="detail-line")

                with Vertical(classes="scope-panel"):
                    yield Label("What We're Confirming", classes="panel-heading")
                    yield Label(f"  Scope: {d.scope.name}", classes="detail-line")
                    yield Label(f"  {d.scope.description}", classes="detail-line")
                    yield Label("", classes="detail-line")
                    yield Label(
                        f"  Archetypes: {len(d.archetypes)}  |  "
                        f"Domains: {len(d.domains)}  |  "
                        f"Capabilities: {len(d.capabilities)}",
                        classes="detail-line",
                    )
                    yield Label(
                        f"  Policies: {len(d.policies)}  |  "
                        f"Connectors: {len(d.connectors)}  |  "
                        f"Bindings: {len(d.bindings)}",
                        classes="detail-line",
                    )

                total = self._compute_total_assertions(d)
                est_minutes = max(1, total // 4)

                with Vertical(classes="onboarding-panel"):
                    yield Label("How This Works", classes="panel-heading")
                    yield Label(
                        "  We extracted a model of your expertise from available sources.",
                        classes="detail-line",
                    )
                    yield Label(
                        "  You'll review each assertion one at a time.",
                        classes="detail-line",
                    )
                    yield Label("", classes="detail-line")
                    yield Label("  Your three options for each assertion:", classes="detail-line")
                    yield Label(
                        "    Confirm [Enter] — This is accurate as written",
                        classes="detail-line",
                    )
                    yield Label(
                        "    Edit [E] — Rewrite in your own words, then save",
                        classes="detail-line",
                    )
                    yield Label(
                        "    Flag [F] — Skip for now and come back to it later",
                        classes="detail-line",
                    )
                    yield Label("", classes="detail-line")
                    yield Label(
                        f"  {total} assertions to review (~{est_minutes} min estimated)",
                        classes="detail-line",
                    )
                    yield Label(
                        "  Your progress saves automatically as you go.",
                        classes="detail-line",
                    )

                with Horizontal(classes="begin-button"):
                    yield Button(
                        "Begin Confirmation [Enter]",
                        id="btn-begin",
                        variant="success",
                    )

            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    @staticmethod
    def _compute_total_assertions(d: Declaration) -> int:
        """Count total assertions across all screens."""
        from tml_engine.confirmation.screens.archetype import _archetype_assertions
        from tml_engine.confirmation.screens.capabilities import _capability_assertions
        from tml_engine.confirmation.screens.domains import _domain_assertions
        from tml_engine.confirmation.screens.edges import _exception_assertions
        from tml_engine.confirmation.screens.flows import _flow_assertions
        from tml_engine.confirmation.screens.policies import _policy_assertions
        from tml_engine.confirmation.screens.skills import _skill_assertions

        total = 0
        for arch in d.archetypes:
            total += len(_archetype_assertions(arch))
        total += len(_domain_assertions(d.domains))
        total += len(_capability_assertions(d.capabilities))
        total += len(_skill_assertions(d.capabilities))
        total += len(_policy_assertions(d.policies))
        total += len(_exception_assertions(d.capabilities))
        total += len(_flow_assertions(d.connectors, d.bindings))
        return total

    def on_mount(self) -> None:
        self.app.update_section_progress("scope", 0, 1)  # type: ignore[attr-defined]
        spine = self.query_one("#progress-spine", ProgressSpineWidget)
        spine.set_active("scope")
        spine.set_counts(self.app.progress_state)  # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-begin":
            self.action_begin()

    def action_begin(self) -> None:
        self.app.update_section_progress("scope", 1, 1)  # type: ignore[attr-defined]
        self.app.switch_screen("archetype")
