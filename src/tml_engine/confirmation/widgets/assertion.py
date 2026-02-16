"""AssertionWidget — displays a single assertion in human-readable prose."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Static


class AssertionWidget(Widget):
    """Displays a single assertion as human-readable prose with source attribution."""

    DEFAULT_CSS = """
    AssertionWidget {
        height: auto;
        padding: 1 2;
        margin: 1 0;
    }

    AssertionWidget .assertion-text {
        padding: 1 2;
        background: $surface;
        border: round $primary;
        text-style: bold;
    }

    AssertionWidget .assertion-source {
        color: $text-muted;
        padding: 0 2;
        margin-top: 1;
    }

    AssertionWidget .assertion-confidence {
        padding: 0 2;
    }

    AssertionWidget .confidence-high {
        color: $success;
    }

    AssertionWidget .confidence-medium {
        color: $warning;
    }

    AssertionWidget .confidence-low {
        color: $error;
    }
    """

    def __init__(
        self,
        assertion_text: str,
        source_label: str = "",
        confidence: str = "high",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._assertion_text = assertion_text
        self._source_label = source_label
        self._confidence = confidence

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._assertion_text, classes="assertion-text")
            if self._source_label:
                yield Label(
                    f"Source: {self._source_label}",
                    classes="assertion-source",
                )
            confidence_class = f"confidence-{self._confidence}"
            yield Label(
                f"Confidence: {self._confidence}",
                classes=f"assertion-confidence {confidence_class}",
            )

    def update_assertion(self, text: str, source: str = "", confidence: str = "high") -> None:
        """Update the assertion content."""
        self._assertion_text = text
        self._source_label = source
        self._confidence = confidence
        self.query_one(".assertion-text", Static).update(text)
        if self._source_label:
            self.query_one(".assertion-source", Label).update(f"Source: {source}")
        confidence_label = self.query_one(".assertion-confidence", Label)
        confidence_label.update(f"Confidence: {confidence}")
        confidence_label.set_classes(f"assertion-confidence confidence-{confidence}")
