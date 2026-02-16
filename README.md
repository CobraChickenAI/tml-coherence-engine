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

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — used for all toolchain operations

## Quick Start

```bash
# Clone and install
git clone https://github.com/CobraChickenAI/tml-coherence-engine.git
cd tml-coherence-engine
uv sync
```

### Try the confirmation TUI (no API key needed)

```bash
uv run tml-engine confirm --mock
```

This launches the full 9-screen confirmation wizard with realistic mock data (a logistics operations manager at a freight brokerage). Navigate with the on-screen controls to see how confirm, correct, and flag work.

### Full workflow (requires Anthropic API key)

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 1. Initialize a project (creates .tml/coherence.db)
uv run tml-engine init

# 2. Extract from a web source
uv run tml-engine extract web --url https://example.com/about --identity you@company.com

# 3. Launch the confirmation surface
uv run tml-engine confirm --identity you@company.com

# 4. Export the confirmed Declaration
uv run tml-engine export --identity you@company.com --format json --output declaration.json
```

Or run an adaptive interview instead of web extraction:

```bash
uv run tml-engine interview --identity you@company.com
```

### Other commands

```bash
# Check project status (primitive counts, confirmation progress)
uv run tml-engine status

# Compute the organizational graph
uv run tml-engine graph --scope <scope-id> --show-flows --show-automation

# Export as YAML
uv run tml-engine export --identity you@company.com --format yaml --output declaration.yaml
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests (164 tests)
make test

# Lint + format check
make check

# Format code
make fmt
```

## Project Structure

```
src/tml_engine/
├── cli.py           # Typer CLI (init, status, extract, interview, confirm, serve, export, graph)
├── pipeline.py      # End-to-end: extract → structure → persist → build Declaration
├── models/          # Pydantic v2 models for all nine TML primitives + Declaration
├── extractors/      # Core extractors (web, interview) + plugin interface
│   └── plugins/     # Integration extractors (Atlassian, etc. — planned)
├── structurer/      # LLM-based raw content → TML primitive conversion
├── confirmation/    # Textual TUI confirmation surface (9 screens, 4 widgets)
├── identity/        # Pluggable identity providers (local SQLite default)
├── graph/           # OrganizationalGraph computation from Declarations
├── storage/         # Async SQLite persistence with Provenance table
└── export/          # JSON/YAML Declaration export
```

## Stack

- Python 3.11+, Pydantic v2, Textual, httpx, BeautifulSoup4
- Anthropic Python SDK for LLM structuring and adaptive interviews
- SQLite (aiosqlite) for local storage
- Typer for CLI, Rich for console output

## Status

Stages 1–6 complete. The local tool is fully functional: extract from web or interview, confirm via TUI, export validated Declarations with provenance trails.

- **Done:** Foundation, Confirmation Surface, Core Extractors, Adaptive Interview, Identity + Graph, Local Hardening (e2e validated)
- **Next:** Integration plugins (Atlassian extractor)
- **Deferred:** Web serving (textual-web), PyPI publishing

## License

MIT — see [LICENSE](LICENSE).

This project implements the [TML specification](https://github.com/CobraChickenAI/themissinglayer), which is licensed under CC BY-SA 4.0. See [NOTICE](NOTICE) for attribution details.
