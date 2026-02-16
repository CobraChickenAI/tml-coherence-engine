"""ArchetypeScreen — confirms role, responsibilities, authority, and boundaries."""

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
from tml_engine.models.primitives import Archetype


def _archetype_assertions(arch: Archetype) -> list[dict]:
    """Generate human-readable assertions from an Archetype primitive."""
    assertions: list[dict] = []

    assertions.append(
        {
            "text": (f"Your role is {arch.role_name}. {arch.role_description}"),
            "field": "role",
        }
    )

    for i, resp in enumerate(arch.primary_responsibilities):
        assertions.append(
            {
                "text": f"One of your primary responsibilities is: {resp}",
                "field": f"responsibility_{i}",
            }
        )

    for i, auth in enumerate(arch.decision_authority):
        assertions.append(
            {
                "text": f"You have authority to: {auth}",
                "field": f"authority_{i}",
            }
        )

    for i, boundary in enumerate(arch.accountability_boundaries):
        assertions.append(
            {
                "text": f"Outside your scope: {boundary}",
                "field": f"boundary_{i}",
            }
        )

    return assertions


class ArchetypeScreen(Screen):
    """Confirms the Archetype primitive — role, responsibilities, authority."""

    DEFAULT_CSS = """
    ArchetypeScreen {
        layout: horizontal;
    }

    ArchetypeScreen .main-content {
        width: 1fr;
        padding: 1 2;
    }

    ArchetypeScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    ArchetypeScreen .assertion-counter {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("q", "app.quit", "Quit"),
    ]

    def __init__(self, archetype: Archetype, **kwargs) -> None:
        super().__init__(**kwargs)
        self.archetype = archetype
        self._assertions = _archetype_assertions(archetype)
        self._current_index = 0
        self._responses: dict[int, str] = {}  # index -> "confirmed"|"corrected"|"flagged"
        self._corrections: dict[int, str] = {}  # index -> corrected text

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Your Role", classes="screen-title")
                yield Static("", id="counter", classes="assertion-counter")
                yield AssertionWidget(
                    assertion_text="",
                    source_label=f"Extracted from: {self.archetype.source.source_type}",
                    id="assertion",
                )
                yield ResponseWidget(id="response")
                yield InlineEditorWidget(id="editor")
            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    def on_mount(self) -> None:
        self._show_current()

    def _show_current(self) -> None:
        if self._current_index >= len(self._assertions):
            self.app.switch_screen("domains")
            return
        assertion = self._assertions[self._current_index]
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
            source=f"Extracted from: {self.archetype.source.source_type}",
        )
        self.query_one("#counter", Static).update(
            f"Assertion {self._current_index + 1} of {len(self._assertions)}"
        )

    def _advance(self) -> None:
        self._current_index += 1
        self._show_current()

    def _record_provenance(self, action: str, corrected_text: str | None = None) -> None:
        """Record a confirmation action as Provenance on the Declaration."""
        assertion = self._assertions[self._current_index]
        declaration = self.app.declaration  # type: ignore[attr-defined]
        actor = declaration.scope.owner_identity
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
        self.archetype.confirmation = record
        entry = make_provenance_entry(
            scope_id=self.archetype.scope_id,
            primitive_id=self.archetype.id,
            primitive_type="archetype",
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
        pass  # Stay on current assertion
