"""PoliciesScreen — confirms rules, constraints, and guardrails."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tml_engine.confirmation.widgets.assertion import AssertionWidget
from tml_engine.confirmation.widgets.editor import InlineEditorWidget
from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.confirmation.widgets.response import ResponseWidget
from tml_engine.models.primitives import Policy


def _policy_assertions(policies: list[Policy]) -> list[dict]:
    """Generate human-readable assertions from Policy primitives."""
    assertions: list[dict] = []
    for policy in policies:
        enforcement = "This rule can never be broken." if policy.enforcement_level == "hard" else "This rule can be overridden with good reason."
        assertions.append({
            "text": (
                f"{policy.name}: {policy.rule} "
                f"{enforcement}"
            ),
            "policy_id": policy.id,
            "field": "policy",
        })
    return assertions


class PoliciesScreen(Screen):
    """Confirms Policy primitives — rules, constraints, guardrails."""

    DEFAULT_CSS = """
    PoliciesScreen {
        layout: horizontal;
    }

    PoliciesScreen .main-content {
        width: 1fr;
        padding: 1 2;
    }

    PoliciesScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    PoliciesScreen .assertion-counter {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(self, policies: list[Policy], **kwargs) -> None:
        super().__init__(**kwargs)
        self.policies = policies
        self._assertions = _policy_assertions(policies)
        self._current_index = 0
        self._responses: dict[int, str] = {}
        self._corrections: dict[int, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Rules & Constraints", classes="screen-title")
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
            self.app.switch_screen("edges")
            return
        assertion = self._assertions[self._current_index]
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
        )
        self.query_one("#counter", Static).update(
            f"Policy {self._current_index + 1} of {len(self._assertions)}"
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
