"""JSON export of Declarations."""

from __future__ import annotations

from pathlib import Path

from tml_engine.models.declaration import Declaration


def export_declaration_json(declaration: Declaration, output_path: Path) -> None:
    """Export a Declaration as JSON."""
    output_path.write_text(declaration.model_dump_json(indent=2))
