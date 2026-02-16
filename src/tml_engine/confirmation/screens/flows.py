"""FlowsScreen — confirms Connectors and Bindings (how expertise flows)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from tml_engine.confirmation.provenance import make_confirmation_record, make_provenance_entry
from tml_engine.confirmation.widgets.assertion import AssertionWidget
from tml_engine.confirmation.widgets.editor import InlineEditorWidget
from tml_engine.confirmation.widgets.progress import ProgressSpineWidget
from tml_engine.confirmation.widgets.response import ResponseWidget
from tml_engine.models.identity import ConfirmationStatus
from tml_engine.models.primitives import Binding, Connector


def _flow_assertions(connectors: list[Connector], bindings: list[Binding]) -> list[dict]:
    """Generate human-readable assertions from Connector and Binding primitives."""
    assertions: list[dict] = []

    for conn in connectors:
        assertions.append(
            {
                "text": (
                    f"Input flow: {conn.name}. "
                    f"You receive information from {conn.reads_from} "
                    f"({conn.reads_from_type}). "
                    f"{conn.description}"
                ),
                "primitive_id": conn.id,
                "primitive_type": "connector",
                "field": "connector",
            }
        )

    for bind in bindings:
        assertions.append(
            {
                "text": (
                    f"Output flow: {bind.name}. "
                    f"Your decisions feed into {bind.writes_to} "
                    f"({bind.writes_to_type}). "
                    f"{bind.description}"
                ),
                "primitive_id": bind.id,
                "primitive_type": "binding",
                "field": "binding",
            }
        )

    return assertions


class FlowsScreen(Screen):
    """Confirms Connectors and Bindings — how expertise flows between domains."""

    DEFAULT_CSS = """
    FlowsScreen {
        layout: horizontal;
    }

    FlowsScreen .main-content {
        width: 1fr;
        padding: 1 2;
    }

    FlowsScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    FlowsScreen .assertion-counter {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(
        self,
        connectors: list[Connector],
        bindings: list[Binding],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.connectors = connectors
        self.bindings = bindings
        self._assertions = _flow_assertions(connectors, bindings)
        self._current_index = 0
        self._responses: dict[int, str] = {}
        self._corrections: dict[int, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Information Flows", classes="screen-title")
                yield Static("", id="counter", classes="assertion-counter")
                yield AssertionWidget(assertion_text="", id="assertion")
                yield ResponseWidget(id="response")
                yield InlineEditorWidget(id="editor")
            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    def on_mount(self) -> None:
        if not self._assertions:
            self.query_one("#counter", Static).update("No flows to confirm")
            self.call_later(self._skip)
        else:
            self._show_current()

    def _skip(self) -> None:
        self.app.switch_screen("summary")

    def _show_current(self) -> None:
        if self._current_index >= len(self._assertions):
            self.app.switch_screen("summary")
            return
        assertion = self._assertions[self._current_index]
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
        )
        self.query_one("#counter", Static).update(
            f"Flow {self._current_index + 1} of {len(self._assertions)}"
        )

    def _advance(self) -> None:
        self._current_index += 1
        self._show_current()

    def _record_provenance(self, action: str, corrected_text: str | None = None) -> None:
        """Record a confirmation action as Provenance on the Declaration."""
        assertion = self._assertions[self._current_index]
        declaration = self.app.declaration  # type: ignore[attr-defined]
        actor = declaration.scope.owner_identity
        primitive_id = assertion["primitive_id"]
        primitive_type = assertion["primitive_type"]
        # Find the actual primitive to attach the confirmation
        if primitive_type == "connector":
            primitive = next(c for c in self.connectors if c.id == primitive_id)
        else:
            primitive = next(b for b in self.bindings if b.id == primitive_id)
        status_map = {
            "confirmed": ConfirmationStatus.CONFIRMED,
            "corrected": ConfirmationStatus.CORRECTED,
            "flagged": ConfirmationStatus.FLAGGED,
        }
        record = make_confirmation_record(
            status=status_map[action],
            actor=actor,
            original_text=assertion["text"],
            corrected_text=corrected_text,
        )
        primitive.confirmation = record
        entry = make_provenance_entry(
            scope_id=primitive.scope_id,
            primitive_id=primitive.id,
            primitive_type=primitive_type,
            action=action,
            actor=actor,
            details={"field": assertion["field"], "assertion_text": assertion["text"]},
        )
        declaration.provenance.append(entry)

    def on_response_widget_confirmed(self, event: ResponseWidget.Confirmed) -> None:
        self._responses[self._current_index] = "confirmed"
        self._record_provenance("confirmed")
        self._advance()

    def on_response_widget_correction_requested(
        self, event: ResponseWidget.CorrectionRequested
    ) -> None:
        assertion = self._assertions[self._current_index]
        self.query_one("#editor", InlineEditorWidget).show(assertion["text"])

    def on_response_widget_flagged(self, event: ResponseWidget.Flagged) -> None:
        self._responses[self._current_index] = "flagged"
        self._record_provenance("flagged")
        self._advance()

    def on_inline_editor_widget_submitted(self, event: InlineEditorWidget.Submitted) -> None:
        self._responses[self._current_index] = "corrected"
        self._corrections[self._current_index] = event.corrected_text
        self._record_provenance("corrected", corrected_text=event.corrected_text)
        self._advance()

    def on_inline_editor_widget_cancelled(self, event: InlineEditorWidget.Cancelled) -> None:
        pass
