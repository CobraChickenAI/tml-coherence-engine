# TML Coherence Engine

## What This Is
A Python tool that extracts human expertise from multiple sources (web, interviews, and pluggable integrations), structures it as TML (The Missing Layer) primitive instances, and presents a Textual TUI confirmation surface where humans validate the extracted representation. Output is a Declaration — the versioned, validated, diffable root of trust. Multiple Declarations compose into an OrganizationalGraph. Extraction and confirmation are a single motion — primitives are born operational.

The core engine ships with two extractors that require zero system access: the adaptive interview and the web scraper. Integration extractors (Atlassian, Notion, SharePoint, etc.) are plugins built after the core is working.

## TML Primitives (the nine, closed set)
```
          Context        Control        Interaction
Boundary  Scope          View           Connector
Commit    Domain         Archetype      Binding
Truth     Capability     Policy         Provenance
```
Every primitive MUST declare its Scope. Provenance is emitted for all significant actions. The Declaration is the root of trust. This set is closed — no additional primitives.

## Stack
- Python 3.11+, Textual (latest), Pydantic v2, httpx, beautifulsoup4
- Anthropic Python SDK for LLM structuring and adaptive interviews
- SQLite for local storage (with dedicated Provenance table)
- Click or Typer for CLI
- Integration plugins (optional): Atlassian MCP, Google Workspace identity, etc.

## Project Structure
- `src/tml_engine/` — all source code
- `src/tml_engine/models/primitives.py` — all nine TML primitive Pydantic models
- `src/tml_engine/models/identity.py` — HumanIdentity + ConfirmationRecord
- `src/tml_engine/models/declaration.py` — Declaration (versioned root of trust)
- `src/tml_engine/models/graph.py` — OrganizationalGraph, DecisionFlow, Dependency, AutomationCandidate
- `src/tml_engine/extractors/` — core extractors (web, interview) + base interface
- `src/tml_engine/extractors/plugins/` — integration extractors (atlassian, etc.)
- `src/tml_engine/structurer/` — LLM-based raw content → TML primitive conversion
- `src/tml_engine/confirmation/` — Textual TUI application (each screen is a View)
- `src/tml_engine/graph/` — OrganizationalGraph computation from Declarations
- `src/tml_engine/storage/` — SQLite persistence (primitives + provenance)
- `src/tml_engine/export/` — JSON/YAML export of Declarations
- `templates/` — web scrape configuration templates
- `tests/` — pytest test suite

## Code Style
- Type hints on all functions and variables
- Async for all I/O operations (httpx, database, API calls)
- Pydantic v2 for ALL data models — never use plain dicts for structured data
- No unnecessary abstractions — build exactly what's needed for the current stage
- Docstrings on public functions only, skip the obvious ones
- Use `pathlib.Path` not string paths

## How to Verify
- `pytest` runs the test suite
- `python -m tml_engine.cli` runs the CLI
- `textual run src/tml_engine/confirmation/app.py` for TUI dev iteration

## Key Architectural Rules
- Every data structure is an instance of one of the nine TML primitives (or a sub-component of one)
- Every primitive MUST have a scope_id (except the root Scope)
- Confirmation status is tracked at the individual primitive level
- Every confirmation, correction, and flag generates a Provenance entry
- Human-readable text is generated FROM primitives for display — never show schema/field names
- The confirmation surface presents ONE assertion at a time in plain English
- Each confirmation screen is conceptually a View — a filtered projection of the Declaration
- All extractors produce `RawExtractionResult`, never TML primitives directly
- The structurer (LLM) is the ONLY thing that converts raw content to primitive instances
- Capabilities contain DecisionFactors, ExceptionRules, and SkillReferences as internal structure
- A Declaration is the complete confirmed architecture for a Scope
- OrganizationalGraph is computed from multiple Declarations, never stored separately
- Extraction → structuring → confirmation → Declaration is one continuous flow

## Build Stages (in order)
1. Foundation: project scaffold, all nine Pydantic primitive models + Declaration + OrganizationalGraph, SQLite storage with Provenance table, CLI skeleton
2. Confirmation Surface: Textual TUI with all screens (Welcome, Archetype, Domains, Capabilities, Skills, Policies, Edges, Flows, Summary) + widgets. Use mock data.
3. Core Extractors: web scrape + LLM structurer (produces all nine primitive types)
4. Adaptive Interview: Claude-powered five-phase interview (Scope → Archetype → Domains → Capabilities → Policies/Flows) with gap detection and skill association
5. Identity + Distribution + Organizational Graph: pluggable identity provider, textual-web, Declaration export, OrganizationalGraph computation, AutomationCandidate scoring, PyPI packaging
6. Integration Plugins: Atlassian extractor (first plugin), additional extractors and identity providers as needed

## Reference
- Full spec: `SPEC.md` in project root
- TML specification: https://github.com/CobraChickenAI/themissinglayer
- Textual docs: https://textual.textualize.io/
- Pydantic v2 docs: https://docs.pydantic.dev/latest/
- Anthropic SDK: https://docs.anthropic.com/en/docs/
