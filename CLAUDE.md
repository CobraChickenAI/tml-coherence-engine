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
- SQLite (aiosqlite) for local storage (with dedicated Provenance table)
- Typer for CLI, Rich for console output
- Ruff for linting and formatting
- Integration plugins (optional): Atlassian MCP, Google Workspace identity, etc.

## Project Structure
- `src/tml_engine/` — all source code
- `src/tml_engine/cli.py` — Typer CLI entry point (8 commands: init, status, extract, interview, confirm, serve, export, graph)
- `src/tml_engine/models/primitives.py` — all nine TML primitive Pydantic models + sub-components (DecisionFactor, ExceptionRule, SkillReference)
- `src/tml_engine/models/identity.py` — HumanIdentity, ConfirmationRecord, ExtractionSource, ConfirmationStatus
- `src/tml_engine/models/declaration.py` — Declaration (versioned root of trust) with completion tracking
- `src/tml_engine/models/graph.py` — OrganizationalGraph, DecisionFlow, Dependency, AutomationCandidate
- `src/tml_engine/extractors/base.py` — BaseExtractor interface, RawExtractionResult, ContentBlock
- `src/tml_engine/extractors/web.py` — WebExtractor (async httpx crawler + BeautifulSoup4)
- `src/tml_engine/extractors/interview.py` — InterviewEngine (five-phase Claude-powered) + InterviewExtractor adapter
- `src/tml_engine/extractors/plugins/` — integration extractors (atlassian, etc.) — not yet implemented
- `src/tml_engine/structurer/llm.py` — LLMStructurer: raw content → TML primitives via Claude, with confidence tracking
- `src/tml_engine/confirmation/app.py` — CoherenceApp (Textual App) orchestrating 9-screen wizard flow
- `src/tml_engine/confirmation/mock_data.py` — Mock Declaration for development/testing (logistics ops manager)
- `src/tml_engine/confirmation/provenance.py` — Helpers for ConfirmationRecord and ProvenanceEntry generation
- `src/tml_engine/confirmation/screens/` — 9 screens: welcome, archetype, domains, capabilities, skills, policies, edges, flows, summary
- `src/tml_engine/confirmation/widgets/` — 4 widgets: assertion, response, editor, progress
- `src/tml_engine/graph/compute.py` — OrganizationalGraph computation (Stage 5 placeholder)
- `src/tml_engine/storage/sqlite.py` — Async SQLite persistence (identities, extractions, primitives, provenance, declarations, interview_sessions)
- `src/tml_engine/export/json.py` — JSON export of Declarations
- `src/tml_engine/export/yaml.py` — YAML export of Declarations
- `templates/web_scrape/default.yaml` — default web scrape configuration
- `tests/` — pytest test suite (109 tests across 9 files)

## Code Style
- Type hints on all functions and variables
- Modern Python 3.11+ syntax: `str | None` over `Optional[str]`, `StrEnum` over `str, Enum`
- Async for all I/O operations (httpx, database, API calls)
- Pydantic v2 for ALL data models — never use plain dicts for structured data
- No unnecessary abstractions — build exactly what's needed for the current stage
- Docstrings on public functions only, skip the obvious ones
- Use `pathlib.Path` not string paths

## How to Verify
- `pytest` — runs the full test suite (109 tests)
- `ruff check src/ tests/` — lint check
- `ruff format --check src/ tests/` — format check
- `python -m tml_engine.cli` — runs the CLI
- `textual run src/tml_engine/confirmation/app.py` — TUI dev iteration

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
1. ~~Foundation: project scaffold, all nine Pydantic primitive models + Declaration + OrganizationalGraph, SQLite storage with Provenance table, CLI skeleton~~ **DONE**
2. ~~Confirmation Surface: Textual TUI with all screens (Welcome, Archetype, Domains, Capabilities, Skills, Policies, Edges, Flows, Summary) + widgets. Use mock data.~~ **DONE**
3. ~~Core Extractors: web scrape + LLM structurer (produces all nine primitive types)~~ **DONE**
4. ~~Adaptive Interview: Claude-powered five-phase interview (Scope → Archetype → Domains → Capabilities → Policies/Flows) with gap detection and skill association~~ **DONE**
5. Identity + Distribution + Organizational Graph: pluggable identity provider, textual-web, Declaration export, OrganizationalGraph computation, AutomationCandidate scoring, PyPI packaging — **NEXT**
6. Integration Plugins: Atlassian extractor (first plugin), additional extractors and identity providers as needed

## Current State & Known Gaps
Stages 1-4 are complete. The individual components (extractors, structurer, TUI, storage) all work independently. The main gap before Stage 5 is **pipeline wiring** — connecting these components end-to-end in the CLI:

- **CLI `extract` doesn't persist.** Runs web extractor but doesn't pass results through structurer or store primitives in SQLite.
- **CLI `interview` doesn't persist.** Runs interview but doesn't store the extraction result or structured primitives.
- **CLI `confirm` can't load from storage.** Only works with mock data (`--mock`). Needs to build a Declaration from stored primitives for a given identity.
- **CLI `export` is stubbed.** The export functions (`export/json.py`, `export/yaml.py`) are implemented but the CLI command doesn't call them.
- **`graph/compute.py` is a placeholder.** OrganizationalGraph computation from Declarations is Stage 5 work.

These gaps are the natural boundary between "components built" (Stages 1-4) and "system integrated" (Stage 5).

## Reference
- Full spec: `SPEC.md` in project root
- TML specification: https://github.com/CobraChickenAI/themissinglayer
- Textual docs: https://textual.textualize.io/
- Pydantic v2 docs: https://docs.pydantic.dev/latest/
- Anthropic SDK: https://docs.anthropic.com/en/docs/
