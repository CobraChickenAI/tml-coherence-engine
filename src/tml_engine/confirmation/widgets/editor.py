"""InlineEditorWidget — text editor for corrections."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, TextArea


class InlineEditorWidget(Widget):
    """Inline text editor for correcting assertions.

    Appears when the user selects Correct. Pre-populated with the
    current assertion text. Submit with the Save button or Ctrl+S,
    cancel with Escape.
    """

    DEFAULT_CSS = """
    InlineEditorWidget {
        height: auto;
        padding: 1 2;
        display: none;
    }

    InlineEditorWidget.visible {
        display: block;
    }

    InlineEditorWidget TextArea {
        height: 6;
        margin: 1 0;
    }

    InlineEditorWidget .editor-label {
        color: $warning;
        text-style: bold;
    }

    InlineEditorWidget .editor-buttons {
        height: auto;
        align: center middle;
    }

    InlineEditorWidget Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "submit", "Save"),
    ]

    @dataclass
    class Submitted(Message):
        """User submitted a correction."""

        corrected_text: str

    @dataclass
    class Cancelled(Message):
        """User cancelled the correction."""

    def __init__(self, initial_text: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._initial_text = initial_text

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Rewrite this in your own words:", classes="editor-label")
            yield TextArea(self._initial_text, id="correction-input")
            from textual.containers import Horizontal

            with Horizontal(classes="editor-buttons"):
                yield Button("Save [Ctrl+S]", id="btn-save", variant="success")
                yield Button("Cancel [Esc]", id="btn-cancel", variant="error")

    def show(self, text: str = "") -> None:
        """Show the editor with the given text."""
        self._initial_text = text
        textarea = self.query_one("#correction-input", TextArea)
        textarea.load_text(text)
        self.add_class("visible")
        textarea.focus()

    def hide(self) -> None:
        """Hide the editor."""
        self.remove_class("visible")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self.action_submit()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_submit(self) -> None:
        textarea = self.query_one("#correction-input", TextArea)
        self.post_message(self.Submitted(corrected_text=textarea.text))
        self.hide()

    def action_cancel(self) -> None:
        self.post_message(self.Cancelled())
        self.hide()
