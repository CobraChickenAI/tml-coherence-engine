"""PoliciesScreen — confirms rules, constraints, and guardrails."""

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
from tml_engine.models.primitives import Policy


def _policy_assertions(policies: list[Policy]) -> list[dict]:
    """Generate human-readable assertions from Policy primitives."""
    assertions: list[dict] = []
    total = len(policies)
    for i, policy in enumerate(policies):
        level = "Hard" if policy.enforcement_level == "hard" else "Soft"
        enforcement = (
            "This rule can never be broken."
            if policy.enforcement_level == "hard"
            else "This rule can be overridden with good reason."
        )
        assertions.append(
            {
                "text": (f"{policy.name}: {policy.rule} {enforcement}"),
                "policy_id": policy.id,
                "field": "policy",
                "group": policy.name,
                "group_label": f"{level} Rule ({i + 1} of {total})",
            }
        )
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
        overflow-y: auto;
    }

    PoliciesScreen .screen-title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    PoliciesScreen .group-header {
        text-style: italic;
        color: $secondary;
        text-align: center;
        padding: 0 0 1 0;
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
                yield Static("", id="group-header", classes="group-header")
                yield Static("", id="counter", classes="assertion-counter")
                yield AssertionWidget(assertion_text="", id="assertion")
                yield ResponseWidget(id="response")
                yield InlineEditorWidget(id="editor")
            yield ProgressSpineWidget(id="progress-spine")
        yield Footer()

    def on_mount(self) -> None:
        self.app.update_section_progress("policies", 0, len(self._assertions))  # type: ignore[attr-defined]
        spine = self.query_one("#progress-spine", ProgressSpineWidget)
        spine.set_active("policies")
        spine.set_counts(self.app.progress_state)  # type: ignore[attr-defined]
        self._show_current()

    def _show_current(self) -> None:
        if self._current_index >= len(self._assertions):
            self.app.switch_screen("edges")
            return
        assertion = self._assertions[self._current_index]
        group = assertion.get("group", "")
        group_label = assertion.get("group_label", "")
        self.query_one("#group-header", Static).update(f"{group} — {group_label}" if group else "")
        self.query_one("#assertion", AssertionWidget).update_assertion(
            text=assertion["text"],
        )
        self.query_one("#counter", Static).update(
            f"Policy {self._current_index + 1} of {len(self._assertions)}"
        )
        self.query_one("#response", ResponseWidget).focus()

    def _advance(self) -> None:
        confirmed = sum(1 for v in self._responses.values() if v in ("confirmed", "corrected"))
        self.app.update_section_progress("policies", confirmed, len(self._assertions))  # type: ignore[attr-defined]
        self.query_one("#progress-spine", ProgressSpineWidget).set_counts(
            self.app.progress_state  # type: ignore[attr-defined]
        )
        self._current_index += 1
        self._show_current()

    async def _record_provenance(self, action: str, corrected_text: str | None = None) -> None:
        """Record a confirmation action as Provenance on the Declaration."""
        assertion = self._assertions[self._current_index]
        declaration = self.app.declaration  # type: ignore[attr-defined]
        actor = declaration.scope.owner_identity
        policy_id = assertion["policy_id"]
        policy = next(p for p in self.policies if p.id == policy_id)
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
        policy.confirmation = record
        entry = make_provenance_entry(
            scope_id=policy.scope_id,
            primitive_id=policy.id,
            primitive_type="policy",
            action=action,
            actor=actor,
            details={"field": assertion["field"], "assertion_text": assertion["text"]},
        )
        declaration.provenance.append(entry)

        await self.app.persist_confirmation(
            primitive_id=policy.id,
            primitive_type="policy",
            scope_id=policy.scope_id,
            status=action,
            actor_email=actor.email,
            provenance_entry=entry,
        )

    async def on_response_widget_confirmed(self, event: ResponseWidget.Confirmed) -> None:
        self._responses[self._current_index] = "confirmed"
        await self._record_provenance("confirmed")
        self._advance()

    def on_response_widget_correction_requested(
        self, event: ResponseWidget.CorrectionRequested
    ) -> None:
        assertion = self._assertions[self._current_index]
        self.query_one("#editor", InlineEditorWidget).show(assertion["text"])

    async def on_response_widget_flagged(self, event: ResponseWidget.Flagged) -> None:
        self._responses[self._current_index] = "flagged"
        await self._record_provenance("flagged")
        self._advance()

    async def on_inline_editor_widget_submitted(self, event: InlineEditorWidget.Submitted) -> None:
        self._responses[self._current_index] = "corrected"
        self._corrections[self._current_index] = event.corrected_text
        await self._record_provenance("corrected", corrected_text=event.corrected_text)
        self._advance()

    def on_inline_editor_widget_cancelled(self, event: InlineEditorWidget.Cancelled) -> None:
        self.query_one("#response", ResponseWidget).focus()
