"""SummaryScreen — displays the complete Declaration and offers export options."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.models.declaration import Declaration


class SummaryScreen(Screen):
    """Final screen: shows the complete Declaration summary and export options."""

    DEFAULT_CSS = """
    SummaryScreen {
        layout: horizontal;
    }

    SummaryScreen .main-content {
        width: 1fr;
        padding: 2 4;
        overflow-y: auto;
    }

    SummaryScreen .summary-title {
        text-style: bold;
        text-align: center;
        padding: 1 0 2 0;
        color: $success;
    }

    SummaryScreen .section-panel {
        padding: 1 2;
        margin: 1 0;
        border: round $secondary;
        background: $surface;
        height: auto;
    }

    SummaryScreen .section-heading {
        text-style: bold;
        padding: 0 0 1 0;
    }

    SummaryScreen .detail-line {
        padding: 0 1;
    }

    SummaryScreen .completion-bar {
        padding: 1 2;
        text-align: center;
    }

    SummaryScreen .export-buttons {
        align: center middle;
        height: auto;
        padding: 2 0;
    }

    SummaryScreen Button {
        margin: 0 1;
        min-width: 20;
    }
    """

    BINDINGS = [
        ("q", "app.quit", "Quit"),
    ]

    def __init__(self, declaration: Declaration, **kwargs) -> None:
        super().__init__(**kwargs)
        self.declaration = declaration

    def compose(self) -> ComposeResult:
        yield Header()
        d = self.declaration
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Declaration Summary", classes="summary-title")

                completion = d.compute_completion()
                yield Static(
                    f"Completion: {completion:.0f}%  |  "
                    f"Confirmed: {d.confirmed_count()}  |  "
                    f"Remaining: {d.unconfirmed_count()}",
                    classes="completion-bar",
                )

                # Scope
                with Vertical(classes="section-panel"):
                    yield Label("Scope", classes="section-heading")
                    yield Label(f"  {d.scope.name}: {d.scope.description}", classes="detail-line")

                # Archetypes
                with Vertical(classes="section-panel"):
                    yield Label(f"Archetypes ({len(d.archetypes)})", classes="section-heading")
                    for arch in d.archetypes:
                        yield Label(
                            f"  {arch.role_name} — {arch.identity.display_name}",
                            classes="detail-line",
                        )

                # Domains
                with Vertical(classes="section-panel"):
                    yield Label(f"Domains ({len(d.domains)})", classes="section-heading")
                    for dom in d.domains:
                        yield Label(f"  {dom.name}: {dom.outcome_definition}", classes="detail-line")

                # Capabilities
                with Vertical(classes="section-panel"):
                    yield Label(f"Capabilities ({len(d.capabilities)})", classes="section-heading")
                    for cap in d.capabilities:
                        factors = len(cap.decision_factors)
                        skills = len(cap.skills)
                        exceptions = len(cap.exceptions)
                        yield Label(
                            f"  {cap.name}  [{factors} factors, {skills} skills, {exceptions} exceptions]",
                            classes="detail-line",
                        )

                # Policies
                with Vertical(classes="section-panel"):
                    yield Label(f"Policies ({len(d.policies)})", classes="section-heading")
                    for pol in d.policies:
                        level = "HARD" if pol.enforcement_level == "hard" else "SOFT"
                        yield Label(f"  [{level}] {pol.name}", classes="detail-line")

                # Flows
                total_flows = len(d.connectors) + len(d.bindings)
                with Vertical(classes="section-panel"):
                    yield Label(
                        f"Flows ({total_flows}: {len(d.connectors)} in, {len(d.bindings)} out)",
                        classes="section-heading",
                    )
                    for conn in d.connectors:
                        yield Label(f"  IN:  {conn.name}", classes="detail-line")
                    for bind in d.bindings:
                        yield Label(f"  OUT: {bind.name}", classes="detail-line")

                # Export buttons
                with Horizontal(classes="export-buttons"):
                    yield Button("Export JSON", id="btn-json", variant="primary")
                    yield Button("Export YAML", id="btn-yaml", variant="primary")
                    yield Button("Done", id="btn-done", variant="success")

            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from pathlib import Path

        if event.button.id == "btn-json":
            from tml_engine.export.json import export_declaration_json

            out = Path("declaration.json")
            export_declaration_json(self.declaration, out)
            self.notify(f"Exported to {out}", title="JSON Export")
        elif event.button.id == "btn-yaml":
            from tml_engine.export.yaml import export_declaration_yaml

            out = Path("declaration.yaml")
            export_declaration_yaml(self.declaration, out)
            self.notify(f"Exported to {out}", title="YAML Export")
        elif event.button.id == "btn-done":
            self.app.exit()
