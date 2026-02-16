"""ResponseWidget — Confirm / Correct / Flag buttons with keyboard shortcuts."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button


class ResponseWidget(Widget, can_focus=True):
    """Three-button response: Confirm (Enter), Edit (E), Flag (F)."""

    DEFAULT_CSS = """
    ResponseWidget {
        height: auto;
        padding: 1 2;
        align: center middle;
    }

    ResponseWidget Horizontal {
        align: center middle;
        height: auto;
    }

    ResponseWidget Button {
        margin: 0 2;
        min-width: 20;
    }

    ResponseWidget #btn-confirm {
        background: $success;
        color: $text;
    }

    ResponseWidget #btn-correct {
        background: $warning;
        color: $text;
    }

    ResponseWidget #btn-flag {
        background: $primary;
        color: $text;
    }
    """

    BINDINGS = [
        ("enter", "confirm", "Confirm"),
        ("e", "correct", "Edit"),
        ("f", "flag", "Flag"),
    ]

    @dataclass
    class Confirmed(Message):
        """User confirmed the assertion."""

    @dataclass
    class CorrectionRequested(Message):
        """User wants to correct the assertion."""

    @dataclass
    class Flagged(Message):
        """User flagged the assertion for discussion."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("Confirm [Enter]", id="btn-confirm", variant="success")
            yield Button("Edit [E]", id="btn-correct", variant="warning")
            yield Button("Flag [F]", id="btn-flag", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.post_message(self.Confirmed())
        elif event.button.id == "btn-correct":
            self.post_message(self.CorrectionRequested())
        elif event.button.id == "btn-flag":
            self.post_message(self.Flagged())

    def action_confirm(self) -> None:
        self.post_message(self.Confirmed())

    def action_correct(self) -> None:
        self.post_message(self.CorrectionRequested())

    def action_flag(self) -> None:
        self.post_message(self.Flagged())
