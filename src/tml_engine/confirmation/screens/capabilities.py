"""CapabilitiesScreen — confirms decision logic, factors, heuristics per Domain."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tml_engine.confirmation.widgets.assertion import AssertionWidget
from tml_engine.confirmation.widgets.editor import InlineEditorWidget
from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.confirmation.widgets.response import ResponseWidget
from tml_engine.models.primitives import Capability


def _capability_assertions(capabilities: list[Capability]) -> list[dict]:
    """Generate human-readable assertions from Capability primitives."""
    assertions: list[dict] = []
    for cap in capabilities:
        # Core description
        assertions.append({
            "text": (
                f"You have the capability: {cap.name}. "
                f"{cap.description} "
                f"The outcome is: {cap.outcome}"
            ),
            "capability_id": cap.id,
            "field": "description",
        })

        # Decision factors
        for factor in cap.decision_factors:
            weight_text = f" (weight: {factor.weight})" if factor.weight else ""
            assertions.append({
                "text": (
                    f"When exercising '{cap.name}', you consider: "
                    f"{factor.name} — {factor.description}{weight_text}"
                ),
                "capability_id": cap.id,
                "field": f"factor_{factor.name}",
            })

        # Heuristics
        for heuristic in cap.heuristics:
            assertions.append({
                "text": (
                    f"A rule of thumb for '{cap.name}': {heuristic}"
                ),
                "capability_id": cap.id,
                "field": "heuristic",
            })

        # Anti-patterns
        for anti in cap.anti_patterns:
            assertions.append({
                "text": (
                    f"A bad practice for '{cap.name}' would be: {anti}"
                ),
                "capability_id": cap.id,
                "field": "anti_pattern",
            })

    return assertions


class CapabilitiesScreen(Screen):
    """Confirms Capability primitives — decision logic, factors, heuristics."""

    DEFAULT_CSS = """
    CapabilitiesScreen {
        layout: horizontal;
    }

    CapabilitiesScreen .main-content {
        width: 1fr;
        padding: 1 2;
    }

    CapabilitiesScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    CapabilitiesScreen .assertion-counter {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(self, capabilities: list[Capability], **kwargs) -> None:
        super().__init__(**kwargs)
        self.capabilities = capabilities
        self._assertions = _capability_assertions(capabilities)
        self._current_index = 0
        self._responses: dict[int, str] = {}
        self._corrections: dict[int, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Your Expertise — Decision Logic", classes="screen-title")
                yield Static("", id="counter", classes="assertion-counter")
                yield AssertionWidget(assertion_text="", id="assertion")
                yield ResponseWidget(id="response")
                yield InlineEditorWidget(id="editor")
            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    def on_mount(self) -> None:
        self._show_current()

    def _show_current(self) -> None:
        if self._current_index >= len(self._assertions):
            self.app.switch_screen("skills")
            return
        assertion = self._assertions[self._current_index]
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
        )
        self.query_one("#counter", Static).update(
            f"Capability {self._current_index + 1} of {len(self._assertions)}"
        )

    def _advance(self) -> None:
        self._current_index += 1
        self._show_current()

    def on_response_widget_confirmed(self, event: ResponseWidget.Confirmed) -> None:
        self._responses[self._current_index] = "confirmed"
        self._advance()

    def on_response_widget_correction_requested(
        self, event: ResponseWidget.CorrectionRequested
    ) -> None:
        assertion = self._assertions[self._current_index]
        self.query_one("#editor", InlineEditorWidget).show(assertion["text"])

    def on_response_widget_flagged(self, event: ResponseWidget.Flagged) -> None:
        self._responses[self._current_index] = "flagged"
        self._advance()

    def on_inline_editor_widget_submitted(
        self, event: InlineEditorWidget.Submitted
    ) -> None:
        self._responses[self._current_index] = "corrected"
        self._corrections[self._current_index] = event.corrected_text
        self._advance()

    def on_inline_editor_widget_cancelled(
        self, event: InlineEditorWidget.Cancelled
    ) -> None:
        pass
