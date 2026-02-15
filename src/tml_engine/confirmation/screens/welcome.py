"""WelcomeScreen — establishes Scope and Archetype identity."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.models.declaration import Declaration


class WelcomeScreen(Screen):
    """First screen: shows who is being confirmed and the scope of the Declaration."""

    DEFAULT_CSS = """
    WelcomeScreen {
        layout: horizontal;
    }

    WelcomeScreen .main-content {
        width: 1fr;
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
            with Vertical(classes="main-content"):
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

                with Horizontal(classes="begin-button"):
                    yield Button(
                        "Begin Confirmation [Enter]",
                        id="btn-begin",
                        variant="success",
                    )

            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-begin":
            self.action_begin()

    def action_begin(self) -> None:
        self.app.switch_screen("archetype")
