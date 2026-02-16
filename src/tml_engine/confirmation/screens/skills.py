"""SkillsScreen — confirms skill associations per Capability."""

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
from tml_engine.models.primitives import Capability


def _skill_assertions(capabilities: list[Capability]) -> list[dict]:
    """Generate human-readable assertions from skill references within Capabilities."""
    assertions: list[dict] = []
    for cap in capabilities:
        for skill in cap.skills:
            surface = f" (runs on: {skill.execution_surface})" if skill.execution_surface else ""
            assertions.append(
                {
                    "text": (
                        f"To execute '{cap.name}', you use: "
                        f"{skill.name} — {skill.description}. "
                        f"Type: {skill.skill_type}{surface}"
                    ),
                    "capability_id": cap.id,
                    "skill_id": skill.id,
                    "field": "skill",
                }
            )
    return assertions


class SkillsScreen(Screen):
    """Confirms SkillReferences within Capabilities."""

    DEFAULT_CSS = """
    SkillsScreen {
        layout: horizontal;
    }

    SkillsScreen .main-content {
        width: 1fr;
        padding: 1 2;
    }

    SkillsScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    SkillsScreen .assertion-counter {
        text-align: center;
        color: $text-muted;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [("q", "app.quit", "Quit")]

    def __init__(self, capabilities: list[Capability], **kwargs) -> None:
        super().__init__(**kwargs)
        self.capabilities = capabilities
        self._assertions = _skill_assertions(capabilities)
        self._current_index = 0
        self._responses: dict[int, str] = {}
        self._corrections: dict[int, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(classes="main-content"):
                yield Static("Your Tools & Processes", classes="screen-title")
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
            self.app.switch_screen("policies")
            return
        assertion = self._assertions[self._current_index]
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
        )
        self.query_one("#counter", Static).update(
            f"Skill {self._current_index + 1} of {len(self._assertions)}"
        )

    def _advance(self) -> None:
        self._current_index += 1
        self._show_current()

    def _record_provenance(self, action: str, corrected_text: str | None = None) -> None:
        """Record a confirmation action as Provenance on the Declaration."""
        assertion = self._assertions[self._current_index]
        declaration = self.app.declaration  # type: ignore[attr-defined]
        actor = declaration.scope.owner_identity
        cap_id = assertion["capability_id"]
        skill_id = assertion["skill_id"]
        cap = next(c for c in self.capabilities if c.id == cap_id)
        skill = next(s for s in cap.skills if s.id == skill_id)
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
        skill.confirmation = record
        entry = make_provenance_entry(
            scope_id=cap.scope_id,
            primitive_id=skill.id,
            primitive_type="skill_reference",
            action=action,
            actor=actor,
            details={
                "field": assertion["field"],
                "capability_id": cap_id,
                "assertion_text": assertion["text"],
            },
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
