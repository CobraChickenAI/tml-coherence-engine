"""DomainsScreen — confirms accountability areas (Domain primitives)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tml_engine.confirmation.widgets.assertion import AssertionWidget
from tml_engine.confirmation.widgets.editor import InlineEditorWidget
from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.confirmation.widgets.response import ResponseWidget
from tml_engine.models.primitives import Domain


def _domain_assertions(domains: list[Domain]) -> list[dict]:
    """Generate human-readable assertions from Domain primitives."""
    assertions: list[dict] = []
    for domain in domains:
        assertions.append({
            "text": (
                f"You are accountable for {domain.name}. "
                f"{domain.description} "
                f"Success looks like: {domain.outcome_definition}"
            ),
            "domain_id": domain.id,
            "field": "domain",
        })
    return assertions


class DomainsScreen(Screen):
    """Confirms Domain primitives — accountability areas."""

    DEFAULT_CSS = """
    DomainsScreen {
        layout: horizontal;
    }

    DomainsScreen .main-content {
        width: 1fr;
        padding: 1 2;
    }

    DomainsScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    DomainsScreen .assertion-counter {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(self, domains: list[Domain], **kwargs) -> None:
        super().__init__(**kwargs)
        self.domains = domains
        self._assertions = _domain_assertions(domains)
        self._current_index = 0
        self._responses: dict[int, str] = {}
        self._corrections: dict[int, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Your Accountability Areas", classes="screen-title")
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
            self.app.switch_screen("capabilities")
            return
        assertion = self._assertions[self._current_index]
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
        )
        self.query_one("#counter", Static).update(
            f"Domain {self._current_index + 1} of {len(self._assertions)}"
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
