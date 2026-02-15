# TML Coherence Engine

Extract human expertise from multiple sources, structure it as [TML](https://github.com/CobraChickenAI/themissinglayer) primitive instances, and present a confirmation surface where humans validate the extracted representation. Output is a Declaration — the versioned, validated, diffable root of trust.

## What It Does

```
Source (Web / Interview / Integrations)
    ↓
Extract → TML Primitives (structured but unvalidated)
    ↓
Coherence Confirmation Surface (Textual TUI)
    ↓
Human confirms, corrects, or flags
    ↓
Validated Declaration → Operational
```

A confirmed primitive is immediately resolvable by an agent, referenceable by a workflow, transferable to another human, and auditable.

## TML Primitives

Nine primitives in a closed 3×3 grid. This set is not extended.

```
          Context        Control        Interaction
Boundary  Scope          View           Connector
Commit    Domain         Archetype      Binding
Truth     Capability     Policy         Provenance
```

## Quick Start

```bash
# Install
uv pip install -e ".[dev]"

# Initialize a project
tml-engine init

# Check status
tml-engine status

# Run tests
make test

# Lint + format
make check
```

## Project Structure

```
src/tml_engine/
├── models/          # Pydantic v2 models for all nine TML primitives + Declaration
├── extractors/      # Core extractors (web, interview) + plugin interface
├── structurer/      # LLM-based raw content → TML primitive conversion
├── confirmation/    # Textual TUI confirmation surface
├── graph/           # OrganizationalGraph computation from Declarations
├── storage/         # SQLite persistence with Provenance table
├── export/          # JSON/YAML Declaration export
└── cli.py           # Typer CLI entry point
```

## Stack

- Python 3.11+, Pydantic v2, Textual, httpx, BeautifulSoup4
- Anthropic Python SDK for LLM structuring and adaptive interviews
- SQLite for local storage
- Typer for CLI

## Build Stages

1. **Foundation** — primitive models, storage, CLI ✅
2. **Confirmation Surface** — Textual TUI with all screens
3. **Core Extractors** — web scrape + LLM structurer
4. **Adaptive Interview** — Claude-powered five-phase interview
5. **Identity + Distribution** — identity providers, export, OrganizationalGraph, PyPI
6. **Integration Plugins** — Atlassian, Notion, SharePoint, etc.

## License

MIT — see [LICENSE](LICENSE).

This project implements the [TML specification](https://github.com/CobraChickenAI/themissinglayer), which is licensed under CC BY-SA 4.0. See [NOTICE](NOTICE) for attribution details.
