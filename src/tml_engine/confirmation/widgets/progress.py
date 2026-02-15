"""ProgressSpineWidget — vertical sidebar showing confirmation progress."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, ProgressBar, Static


class ProgressSpineWidget(Widget):
    """Vertical progress sidebar showing completion state across the Declaration.

    Tracks: Scope, Archetype, Domains, Capabilities, Skills, Policies,
    Exceptions, Flows (Connectors + Bindings).
    """

    DEFAULT_CSS = """
    ProgressSpineWidget {
        width: 32;
        height: 100%;
        padding: 1;
        border-left: solid $primary;
        background: $surface;
    }

    ProgressSpineWidget .progress-title {
        text-style: bold;
        text-align: center;
        padding: 0 0 1 0;
    }

    ProgressSpineWidget .section-label {
        padding: 0 1;
        height: 1;
    }

    ProgressSpineWidget .section-active {
        text-style: bold;
        color: $primary;
    }

    ProgressSpineWidget .section-done {
        color: $success;
    }

    ProgressSpineWidget .section-pending {
        color: $text-muted;
    }

    ProgressSpineWidget ProgressBar {
        padding: 1 1;
    }

    ProgressSpineWidget .overall-label {
        text-align: center;
        text-style: bold;
        padding-top: 1;
    }
    """

    # Section definitions: (key, display_name)
    SECTIONS = [
        ("scope", "Scope"),
        ("archetype", "Role"),
        ("domains", "Domains"),
        ("capabilities", "Capabilities"),
        ("skills", "Skills"),
        ("policies", "Policies"),
        ("edges", "Exceptions"),
        ("flows", "Flows"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._counts: dict[str, tuple[int, int]] = {}  # key -> (confirmed, total)
        self._active_section: str = ""
        self._overall: float = 0.0

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Declaration Progress", classes="progress-title")
            for key, display_name in self.SECTIONS:
                confirmed, total = self._counts.get(key, (0, 0))
                if total > 0:
                    label = f"  {display_name}  [{confirmed}/{total}]"
                else:
                    label = f"  {display_name}  [—]"
                css_class = "section-label"
                if key == self._active_section:
                    css_class += " section-active"
                elif confirmed == total and total > 0:
                    css_class += " section-done"
                else:
                    css_class += " section-pending"
                yield Label(label, id=f"progress-{key}", classes=css_class)
            yield Static("", classes="overall-label", id="overall-pct")
            yield ProgressBar(total=100, show_eta=False, id="overall-bar")

    def set_counts(self, counts: dict[str, tuple[int, int]]) -> None:
        """Update section counts. counts maps section key to (confirmed, total)."""
        self._counts = counts
        self._update_labels()

    def set_active(self, section: str) -> None:
        """Set the currently active section."""
        self._active_section = section
        self._update_labels()

    def _update_labels(self) -> None:
        total_confirmed = 0
        total_items = 0
        for key, display_name in self.SECTIONS:
            confirmed, total = self._counts.get(key, (0, 0))
            total_confirmed += confirmed
            total_items += total
            try:
                label_widget = self.query_one(f"#progress-{key}", Label)
            except Exception:
                continue
            if total > 0:
                text = f"  {display_name}  [{confirmed}/{total}]"
            else:
                text = f"  {display_name}  [—]"
            label_widget.update(text)

            css_class = "section-label"
            if key == self._active_section:
                css_class += " section-active"
            elif confirmed == total and total > 0:
                css_class += " section-done"
            else:
                css_class += " section-pending"
            label_widget.set_classes(css_class)

        if total_items > 0:
            self._overall = (total_confirmed / total_items) * 100.0
        else:
            self._overall = 0.0

        try:
            self.query_one("#overall-pct", Static).update(f"{self._overall:.0f}% Complete")
            self.query_one("#overall-bar", ProgressBar).update(progress=self._overall)
        except Exception:
            pass
