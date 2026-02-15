"""YAML export of Declarations."""

from __future__ import annotations

from pathlib import Path

import yaml

from tml_engine.models.declaration import Declaration


def export_declaration_yaml(declaration: Declaration, output_path: Path) -> None:
    """Export a Declaration as YAML."""
    data = declaration.model_dump(mode="json")
    output_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
