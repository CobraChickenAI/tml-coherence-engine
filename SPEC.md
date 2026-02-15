# TML Coherence Engine — Technical Specification

## Project Identity

**Name:** `tml-coherence-engine`
**Organization:** CobraChicken AI (`cobrachicken.ai`)
**Repository:** `cobrachicken-ai/tml-coherence-engine`
**Primary Author:** Michael
**Version:** 0.1.0 (Foundation)

---

## 1. What This Is

The TML Coherence Engine is a Python-based tool that extracts institutional expertise from multiple sources, structures it as TML (The Missing Layer) primitives, and presents humans with a confirmation surface where they validate and correct the extracted representation of their own knowledge. The extraction and confirmation are a single motion — primitives are born operational, not filed for later review.

This is not a knowledge management system. It does not produce documents, reports, or repositories. It produces validated, identity-anchored, structured decision frameworks that are immediately available for agents, workflows, and other humans to act on.

### Core Loop

```
Source (Confluence / Jira / Web / Interview)
    ↓
Extract → TML Primitives (structured but unvalidated)
    ↓
Anchor to Human Identity (Google Workspace)
    ↓
Coherence Confirmation Surface (Textual TUI / textual-web)
    ↓
Human confirms, corrects, or flags
    ↓
Validated Primitives → Operational (immediately available)
```

### What "Operational" Means

A confirmed primitive is immediately:
- Resolvable by an agent (it can be queried and acted upon)
- Referenceable by a workflow (it can serve as a decision gate)
- Transferable to another human (it can onboard or train)
- Auditable (it has a confirmed-by identity and timestamp)

---

## 2. Architecture Overview

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.11+ | Michael's primary language, Textual ecosystem |
| TUI Framework | Textual (latest) | Rich terminal UI, textual-web for browser serving |
| Data Model | Pydantic v2 | Structured primitives with validation |
| **Core Extractors** | | |
| Extraction — Interview | Claude API (Anthropic SDK) | Adaptive interview via conversational AI. Zero system access required. The primary extraction method. |
| Extraction — Web | httpx + BeautifulSoup4 | Web scraping with async support. Zero system access required. |
| **Integration Extractors (plugins, built after core)** | | |
| Extraction — Atlassian | Atlassian MCP Server | Confluence + Jira access via Model Context Protocol |
| **Other** | | |
| LLM Integration | Anthropic Python SDK | Structuring raw content into TML primitives |
| Identity | Pluggable (Google Workspace first) | Human spine — anchoring primitives to real people |
| Storage | SQLite (local) → GCS (future) | Primitive persistence, confirmation state |
| Packaging | PyPI package + textual-web | `pip install tml-coherence-engine` + browser serving |

### Project Structure

```
tml-coherence-engine/
├── CLAUDE.md                    # Claude Code persistent context
├── SPEC.md                      # This file
├── pyproject.toml               # Project metadata, dependencies
├── README.md
├── src/
│   └── tml_engine/
│       ├── __init__.py
│       ├── cli.py               # Entry point, Textual app launcher
│       ├── models/
│       │   ├── __init__.py
│       │   ├── primitives.py    # All nine TML primitive Pydantic models
│       │   ├── identity.py      # HumanIdentity + ConfirmationRecord
│       │   ├── declaration.py   # Declaration model (versioned root of trust)
│       │   └── graph.py         # OrganizationalGraph, DecisionFlow, Dependency, AutomationCandidate
│       ├── extractors/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract extractor interface
│       │   ├── web.py           # Website scraping extractor (core)
│       │   ├── interview.py     # Adaptive interview extractor (core)
│       │   └── plugins/
│       │       ├── __init__.py
│       │       └── atlassian.py # Confluence + Jira via MCP (integration plugin)
│       ├── structurer/
│       │   ├── __init__.py
│       │   └── llm.py           # Raw content → TML primitives via Claude
│       ├── confirmation/
│       │   ├── __init__.py
│       │   ├── app.py           # Main Textual application
│       │   ├── screens/
│       │   │   ├── __init__.py
│       │   │   ├── welcome.py   # Scope + Archetype identity establishment
│       │   │   ├── archetype.py # Role, responsibilities, authority confirmation
│       │   │   ├── domains.py   # Domain accountability confirmation
│       │   │   ├── capabilities.py  # Decision logic, factors, heuristics
│       │   │   ├── skills.py    # Skill association per Capability
│       │   │   ├── policies.py  # Rules, constraints, guardrails
│       │   │   ├── edges.py     # Exceptions within Capabilities
│       │   │   ├── flows.py     # Connectors + Bindings (multi-Archetype)
│       │   │   └── summary.py   # Complete Declaration + export
│       │   └── widgets/
│       │       ├── __init__.py
│       │       ├── assertion.py  # Assertion presentation widget
│       │       ├── response.py   # Confirm/Correct/Flag widget
│       │       ├── editor.py     # Inline correction editor
│       │       └── progress.py   # Progress spine widget (all nine types)
│       ├── graph/
│       │   ├── __init__.py
│       │   └── compute.py       # OrganizationalGraph computation from Declarations
│       ├── storage/
│       │   ├── __init__.py
│       │   └── sqlite.py        # Local primitive + provenance persistence
│       └── export/
│           ├── __init__.py
│           ├── json.py          # JSON export of Declarations
│           └── yaml.py          # YAML export of Declarations
├── templates/
│   └── web_scrape/
│       └── default.yaml         # Default web scrape configuration
└── tests/
    ├── __init__.py
    ├── test_extractors/
    ├── test_structurer/
    ├── test_confirmation/
    ├── test_graph/
    └── test_models/
```

---

## 3. TML Primitive Data Model

The Coherence Engine produces TML-conformant primitive instances. TML defines exactly nine
primitives in a closed 3×3 grid. This set is not extended. Every model below is an instance
of a TML primitive, not a custom invention.

```
          Context        Control        Interaction
          ───────        ───────        ───────────
Boundary  Scope          View           Connector
Commit    Domain         Archetype      Binding
Truth     Capability     Policy         Provenance
```

The Declaration is the versioned, validated, diffable representation of all primitive
instances and their relationships. It is the single source of authority. The Coherence
Engine builds Declarations by extracting, structuring, and confirming primitives.

### 3.1 Foundation Types

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional


class ConfirmationStatus(str, Enum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    FLAGGED = "flagged"


class HumanIdentity(BaseModel):
    """Anchored to Google Workspace identity. Not a TML primitive —
    this is the real-world anchor that Archetypes reference."""
    email: str
    display_name: str
    title: Optional[str] = None
    department: Optional[str] = None
    workspace_id: Optional[str] = None


class ConfirmationRecord(BaseModel):
    """Tracks who confirmed what and when. Feeds into Provenance."""
    status: ConfirmationStatus
    confirmed_by: HumanIdentity
    confirmed_at: datetime
    original_text: Optional[str] = None
    corrected_text: Optional[str] = None
    flag_reason: Optional[str] = None


class ExtractionSource(BaseModel):
    """Where a primitive was extracted from. Feeds into Provenance."""
    source_type: str  # "confluence", "jira", "web", "interview"
    source_identifier: str  # URL, space key, project key, etc.
    extracted_at: datetime
```

### 3.2 Context Primitives — Where Things Live

```python
class Scope(BaseModel):
    """Bounded organizational or ownership context.
    Every other primitive instance MUST declare its Scope.
    Scopes MAY be nested."""
    id: str
    name: str
    description: str
    parent_scope_id: Optional[str] = None  # For nesting (org → team → individual)
    owner_identity: HumanIdentity  # Who owns this scope
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource


class Domain(BaseModel):
    """Outcome-based accountability boundary for a functional area.
    A Domain MUST own at least one Capability. A Domain MUST declare its Scope.
    In the Coherence Engine, Domains map to the areas where a person makes
    decisions and holds accountability."""
    id: str
    scope_id: str  # MUST declare Scope
    name: str
    description: str
    outcome_definition: str  # What success looks like in this domain
    accountable_archetype_id: str  # Who is accountable
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource


class Capability(BaseModel):
    """The atomic unit of value, defined by the outcome it delivers.
    The locus of logic. A Capability MUST belong to exactly one Domain.
    A Capability MUST declare its Scope.

    In the Coherence Engine, Capabilities are where expertise lives —
    the specific things a person can do, the decisions they can make,
    the judgments they can render. Capabilities contain or reference Skills."""
    id: str
    scope_id: str  # MUST declare Scope
    domain_id: str  # MUST belong to exactly one Domain
    name: str
    description: str
    outcome: str  # What this capability delivers
    # The expertise content — this is the core extraction target
    decision_factors: list["DecisionFactor"]
    heuristics: list[str]  # Rules of thumb
    anti_patterns: list[str]  # Things that indicate a bad decision
    exceptions: list["ExceptionRule"]  # When normal logic gets overridden
    # Skills this capability contains or references
    skills: list["SkillReference"]
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource


class DecisionFactor(BaseModel):
    """A factor within a Capability's decision logic. Not a TML primitive —
    this is internal structure within a Capability."""
    name: str
    description: str
    weight: Optional[str] = None  # "primary", "secondary", "tiebreaker"
    confirmation: Optional[ConfirmationRecord] = None


class ExceptionRule(BaseModel):
    """Edge cases and overrides within a Capability. Not a TML primitive —
    this is internal structure within a Capability. Pure tacit knowledge."""
    trigger: str  # What condition activates this exception
    override_description: str  # What happens when the exception fires
    reason: str  # Why this exception exists
    confirmation: Optional[ConfirmationRecord] = None


class SkillReference(BaseModel):
    """A reference to an executable skill that operationalizes a Capability.
    Not a TML primitive — Skills are execution artifacts that Capabilities
    point to. This is the bridge to SkillPack and agent execution."""
    id: str
    name: str
    description: str
    skill_type: str  # "agent_skill", "workflow", "tool", "process", "manual"
    execution_surface: Optional[str] = None  # Where this skill runs
    skill_uri: Optional[str] = None  # Reference to SkillPack or other registry
    confirmation: Optional[ConfirmationRecord] = None
```

### 3.3 Control Primitives — How It Is Constrained

```python
class View(BaseModel):
    """A filtered projection of one or more Capabilities for a specific caller.
    A View MUST reference at least one Capability. A Capability MUST NOT
    reference a View. A View MUST declare its Scope.

    In the Coherence Engine, Views are what the confirmation surface presents.
    Each screen is a View — a projection of raw primitives into human-readable
    assertions for a specific Archetype to confirm."""
    id: str
    scope_id: str
    name: str
    description: str
    capability_ids: list[str]  # MUST reference at least one
    target_archetype_id: Optional[str] = None  # Who this view is for
    projection_format: str  # "confirmation", "summary", "operational", "export"


class Archetype(BaseModel):
    """A caller role definition that constrains what actions a caller may take.
    An Archetype MUST declare its Scope.

    In the Coherence Engine, Archetypes are the human roles extracted from
    the organization. This is who the person IS in the system — their role,
    their authority, their accountability boundaries."""
    id: str
    scope_id: str
    identity: HumanIdentity  # The real human behind this archetype
    role_name: str
    role_description: str
    primary_responsibilities: list[str]
    decision_authority: list[str]  # What they have authority to decide
    accountability_boundaries: list[str]  # Where their authority ends
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource


class Policy(BaseModel):
    """An enforced rule or constraint governing one or more primitives.
    Policy is authoritative: deny by default. A Policy MUST declare its Scope
    and the primitives it attaches to.

    In the Coherence Engine, Policies capture the rules, constraints, and
    guardrails that govern how Capabilities are exercised. These include
    organizational policies, regulatory constraints, and the person's own
    self-imposed rules."""
    id: str
    scope_id: str
    name: str
    description: str
    rule: str  # The actual constraint in natural language
    attaches_to: list[str]  # Primitive IDs this policy governs
    enforcement_level: str  # "hard" (never violated), "soft" (overridable with reason)
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource
```

### 3.4 Interaction Primitives — How It Crosses Boundaries

```python
class Connector(BaseModel):
    """A governed read access pathway across Scopes or Domains.
    A Connector MUST declare its Scope, the source it reads from,
    and the Policies that govern it.

    In the Coherence Engine, Connectors represent how expertise flows
    INTO a person's domain — what information sources they consume,
    what other Capabilities they depend on for input."""
    id: str
    scope_id: str
    name: str
    reads_from: str  # Source primitive or external system identifier
    reads_from_type: str  # "capability", "domain", "external_system"
    governed_by_policy_ids: list[str]
    description: str
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource


class Binding(BaseModel):
    """A governed write access link that commits effects.
    A Binding MUST declare its Scope, the target it writes to,
    and the Policies that govern it.

    In the Coherence Engine, Bindings represent how expertise flows
    OUT of a person's domain — what downstream systems, people, or
    processes depend on their decisions and outputs."""
    id: str
    scope_id: str
    name: str
    writes_to: str  # Target primitive or external system identifier
    writes_to_type: str  # "capability", "domain", "external_system"
    governed_by_policy_ids: list[str]
    description: str
    confirmation: Optional[ConfirmationRecord] = None
    source: ExtractionSource


class ProvenanceEntry(BaseModel):
    """An immutable, append-only record of origin, change history, and ownership.
    Provenance MUST be emitted for all significant actions. Non-optional.

    In the Coherence Engine, every extraction, structuring, confirmation,
    and correction generates Provenance. This is the audit trail that
    makes the Declaration trustworthy."""
    id: str
    scope_id: str
    primitive_id: str  # What primitive this provenance is about
    primitive_type: str  # Which of the nine
    action: str  # "extracted", "structured", "confirmed", "corrected", "flagged"
    actor: HumanIdentity  # Who did this
    timestamp: datetime
    details: dict  # Action-specific metadata
    previous_state: Optional[dict] = None  # Snapshot before change
```

### 3.5 The Declaration

```python
class Declaration(BaseModel):
    """The versioned, validated, diffable representation of all primitive
    instances and their relationships within a governed system. The single
    source of authority for the system's intended state.

    In the Coherence Engine, a Declaration is the complete confirmed
    architecture for one or more humans within a Scope. It is what
    gets exported, what agents resolve against, what the organization
    can act on."""
    id: str
    version: str
    scope: Scope
    archetypes: list[Archetype]
    domains: list[Domain]
    capabilities: list[Capability]
    views: list[View]
    policies: list[Policy]
    connectors: list[Connector]
    bindings: list[Binding]
    provenance: list[ProvenanceEntry]
    created_at: datetime
    last_confirmed_at: Optional[datetime] = None
    completion_percentage: float = 0.0

    def confirmed_count(self) -> int:
        """Count of all primitives with confirmed status."""
        pass  # Implementation counts across all confirmable primitives

    def unconfirmed_count(self) -> int:
        """Count of primitives still awaiting confirmation."""
        pass
```

### 3.6 Organizational Graph

When multiple Declarations exist within nested Scopes, they compose into an
organizational graph. This is what turns individual expertise extraction into
the "20x company" blueprint — a complete map of how decisions flow between
roles, where dependencies exist, and where automation is possible.

```python
class OrganizationalGraph(BaseModel):
    """Composed view across multiple Declarations within nested Scopes.
    Not a TML primitive — this is a projection (a View) across the
    organization's complete Declaration set."""
    root_scope: Scope
    declarations: list[Declaration]  # All Declarations within this Scope tree

    # Derived relationships (computed from Connectors and Bindings)
    decision_flows: list["DecisionFlow"]  # How decisions cascade between roles
    dependency_map: list["Dependency"]  # Who depends on whose output
    automation_candidates: list["AutomationCandidate"]  # Where agents can take over


class DecisionFlow(BaseModel):
    """A traced path showing how a decision in one Archetype's Domain
    cascades to affect another Archetype's Domain."""
    from_archetype_id: str
    from_capability_id: str
    to_archetype_id: str
    to_capability_id: str
    via_binding_id: str  # The Binding that commits the effect
    via_connector_id: str  # The Connector that reads it downstream
    description: str


class Dependency(BaseModel):
    """An explicit dependency between Capabilities across Archetypes."""
    upstream_capability_id: str
    downstream_capability_id: str
    dependency_type: str  # "blocking", "informing", "gating"
    description: str


class AutomationCandidate(BaseModel):
    """A Capability where the confirmed decision logic + skills suggest
    an agent could handle it. Derived from the completeness of the
    Capability's decision factors, heuristics, exceptions, and skill
    references."""
    capability_id: str
    archetype_id: str
    automation_readiness: float  # 0.0 to 1.0
    missing_elements: list[str]  # What's needed before automation is viable
    recommended_skill_type: str  # "agent_skill", "workflow", "copilot"
    rationale: str
```

---

## 4. Extractors

All extractors implement a common interface and produce the same intermediate format: `RawExtractionResult`. The structurer (Section 5) then converts these into TML primitives.

### Base Interface

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel


class RawExtractionResult(BaseModel):
    """Intermediate format between extraction and structuring."""
    source_type: str  # "confluence", "jira", "web", "interview"
    source_identifier: str  # URL, space key, project key, etc.
    content_blocks: list[ContentBlock]
    metadata: dict
    extracted_at: datetime


class ContentBlock(BaseModel):
    """A unit of extracted content with context."""
    content: str
    content_type: str  # "page", "comment", "issue", "description", "response"
    author: Optional[str] = None  # Who wrote this content
    created_at: Optional[datetime] = None
    context: str  # Where in the source this came from
    url: Optional[str] = None


class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, config: dict) -> RawExtractionResult:
        """Extract content from a source."""
        pass

    @abstractmethod
    async def list_available(self) -> list[dict]:
        """List available sources the user can choose from."""
        pass
```

### 4a. Atlassian Extractor — Integration Plugin (Confluence + Jira)

This is the first integration plugin. It is NOT part of the core engine build.
It demonstrates the pattern for connecting to organizational systems. Build after
the core engine (interview + web scrape) is working end-to-end.

Uses the Atlassian MCP server for authenticated access. The user chooses what to excavate.

**MCP Server:** `https://mcp.atlassian.com/v1/mcp`

**Confluence capabilities:**
- List all spaces the user has access to
- List pages within a space (with option to filter by label, date range, or author)
- Read full page content including comments
- Read page tree hierarchies (parent/child relationships)
- Selective extraction: user picks specific spaces, pages, or page trees

**Jira capabilities:**
- List all projects the user has access to
- Read issues with full description, comments, and history
- Filter by project, assignee, status, date range, label
- Read custom fields and workflows
- Selective extraction: user picks specific projects, boards, or JQL queries

**Selection flow (presented in the TUI):**

```
Atlassian Source Selection
├── Confluence
│   ├── [ ] Space: Engineering Wiki
│   │   ├── [ ] All pages
│   │   ├── [ ] Pages by label: architecture, decisions, runbooks
│   │   └── [ ] Pages modified in last N days
│   ├── [ ] Space: Product
│   └── [ ] Space: Onboarding
└── Jira
    ├── [ ] Project: PLATFORM
    │   ├── [ ] All issues
    │   ├── [ ] Issues assigned to: [person]
    │   └── [ ] Issues by type: Epic, Story, Bug
    ├── [ ] Project: DATA
    └── [ ] Custom JQL: [user input]
```

**Implementation notes:**
- MCP integration uses the Anthropic SDK's MCP client capabilities
- Each MCP tool call returns structured data that maps to ContentBlock
- Pagination is handled automatically — large spaces are crawled completely
- Rate limiting and retry logic built in
- Progress reporting piped to the TUI during extraction

### 4b. Web Scrape Extractor

Scrapes a website and extracts content that reveals expertise, decision patterns, and organizational knowledge.

**Default scrape template** (`templates/web_scrape/default.yaml`):

```yaml
# Web Scrape Configuration
# Modify this template for different site structures

target:
  base_url: ""  # Set by user
  max_depth: 3  # How deep to crawl from base
  max_pages: 100  # Safety limit
  respect_robots: true

include_patterns:
  - "/about*"
  - "/services*"
  - "/solutions*"
  - "/team*"
  - "/blog*"
  - "/case-studies*"
  - "/resources*"

exclude_patterns:
  - "/wp-admin*"
  - "/login*"
  - "/cart*"
  - "*.pdf"
  - "*.jpg"
  - "*.png"

content_selectors:
  # CSS selectors for main content areas
  primary: ["main", "article", ".content", "#content"]
  # Remove noise
  strip: ["nav", "footer", "header", ".sidebar", ".cookie-notice", "script", "style"]

extraction_focus:
  # What to look for in the content
  - expertise_signals: "language indicating specialized knowledge, methodology, frameworks"
  - decision_patterns: "how-to content, process descriptions, evaluation criteria"
  - value_propositions: "what they claim to do better than alternatives"
  - team_expertise: "bios, credentials, specializations"
  - case_studies: "real examples of decisions and outcomes"
```

**Implementation:**
- Uses `httpx` for async HTTP requests
- `BeautifulSoup4` for HTML parsing
- Crawls breadth-first from base URL
- Respects robots.txt by default
- Each page becomes a ContentBlock with URL context
- Deduplication of content across pages
- The scrape template is user-editable before execution

### 4c. Adaptive Interview Extractor

This is the most important extractor. It's a conversational AI interview that fills in gaps left by other extractors, or serves as the primary extraction method when no system sources exist.

**Key design principle:** The interview is ADAPTIVE. It knows what has already been extracted from other sources and focuses specifically on gaps, ambiguities, and tacit knowledge that couldn't be captured from documentation.

**Interview flow:**

```
Phase 1: Context Setting (establishing Scope)
├── If prior extractions exist:
│   "We've already extracted some information about your role
│    from [sources]. I'm going to walk through what we found
│    and ask you to fill in the gaps."
└── If standalone interview:
    "I'd like to understand how you think about your work —
     specifically, what decisions you make and how you make them."
    Establishes: Scope primitive (the bounded context for this person's architecture)

Phase 2: Archetype Discovery (who they are in the system)
├── Open-ended: "Describe your role in your own words"
├── Probing: "What do people come to you for that they can't get elsewhere?"
├── Boundary: "Where does your responsibility end and someone else's begin?"
└── Produces: Archetype primitive (unconfirmed)

Phase 3: Domain Mapping (accountability boundaries)
├── Elicitation: "Walk me through a typical week. What decisions do you make?"
├── Categorization: "These seem to cluster around [X, Y, Z]. Does that match?"
├── Gap detection: "Is there anything you decide that we haven't covered?"
└── Produces: list[Domain] primitives (unconfirmed)

Phase 4: Capability Deep Dive (per Domain — the expertise)
├── Scenario-based: "Tell me about the last time you had to [domain decision]"
├── Factor elicitation: "What did you consider? What mattered most?"
├── Contrast: "What would a bad version of that decision look like?"
├── Heuristic capture: "Do you have any rules of thumb for this?"
├── Exception mining: "When do you throw out everything you just told me?"
├── Skill association: "What tools or processes do you use to execute this?"
└── Produces: Capability primitives with DecisionFactors, ExceptionRules,
    SkillReferences (all unconfirmed)

Phase 5: Policy + Flow Discovery (constraints and interactions)
├── Constraint elicitation: "What rules can you never break, no matter what?"
├── Upstream: "Whose output do you depend on to do your job?"
├── Downstream: "Who depends on your decisions? What breaks if you're wrong?"
└── Produces: Policy, Connector, Binding primitives (unconfirmed)
```

**Implementation:**
- Uses Claude API (Anthropic Python SDK) with a carefully crafted system prompt
- Conversation history maintained for context
- Adaptive branching based on prior extraction results
- Each interview phase maps to specific TML primitive types
- Interview can be paused and resumed (state persisted to SQLite)
- The interview is presented in the same Textual TUI as the confirmation surface

**Claude system prompt structure for interview:**

```
You are conducting an expertise extraction interview. Your goal is to
understand how this person thinks, decides, and acts in their role.

You are NOT gathering information for a report. You are building a
structured representation of their decision-making architecture using
TML primitives: Archetype (who they are), Domain (where they hold
accountability), Capability (what they can do and how they decide),
Policy (what constrains them), and the Connectors/Bindings that show
how their work flows to and from other people.

{if prior_extractions}
We have already extracted the following from {sources}:
{summary of existing primitives by type — Archetypes, Domains, Capabilities, Policies}

Focus on:
- Validating or correcting what was extracted
- Filling gaps in Capability logic (decision factors, heuristics, exceptions)
- Associating Skills to confirmed Capabilities
- Capturing Policies not visible in documentation
- Discovering Connectors (who they depend on) and Bindings (who depends on them)
{/if}

Output format: After each interview phase, produce structured JSON
representing the primitive instances discovered. Use the schema provided.
Every primitive MUST include a scope_id.

Interview style:
- Ask one question at a time
- Use their language, not framework terminology
- Follow interesting threads — don't stick rigidly to the script
- If they mention something unexpected, explore it
- Mirror back what you think you heard and ask them to confirm
```

---

## 5. Structurer (LLM Processing)

The structurer takes RawExtractionResult from any extractor and produces TML primitive instances via Claude. The structurer's job is to map unstructured content to the nine-primitive grid. Every output MUST be a valid instance of one of the nine primitives.

**Process:**

```
RawExtractionResult
    ↓
Content Analysis Prompt → Claude
    ↓
Identifies: Archetypes, Domains, Capabilities (with decision logic,
            heuristics, anti-patterns, exceptions), Policies,
            Connector/Binding relationships, Skill references
    ↓
Structured Output → Pydantic models (all unconfirmed)
    ↓
Scope assignment (all primitives MUST declare Scope)
    ↓
Deduplication + merge with existing primitives
    ↓
Provenance emitted for every primitive created
    ↓
Ready for confirmation surface
```

**Key implementation details:**
- Uses Claude with structured output (JSON mode)
- Multiple passes for complex sources: first pass identifies Archetypes + Domains, second pass extracts Capabilities + Policies, third pass infers Connectors + Bindings
- Deduplication logic handles overlapping content from multiple sources
- Confidence scoring on each extracted primitive (high/medium/low)
- Low-confidence primitives are flagged for interview follow-up
- Every structuring action generates Provenance entries

---

## 6. Confirmation Surface (Textual TUI)

This is the product. Everything else enables this.

### Application Structure

The app is a Textual application using the Screen system for wizard-style navigation. Each screen represents a confirmation phase.

### Screen Flow

Each screen is a View — a projection of TML primitives into human-readable
assertions for the Archetype (person) to confirm.

```
WelcomeScreen
    ↓ (identity confirmed, source context shown — establishing Scope + Archetype)
ArchetypeScreen
    ↓ (role, responsibilities, authority confirmed — Archetype primitive)
DomainsScreen
    ↓ (accountability areas confirmed/added/removed — Domain primitives)
CapabilitiesScreen (one instance per confirmed Domain)
    ↓ (decision logic, factors, heuristics confirmed — Capability primitives)
SkillsScreen (per Capability)
    ↓ (skills referenced, associated, confirmed — SkillReference within Capability)
PoliciesScreen
    ↓ (rules, constraints, guardrails confirmed — Policy primitives)
EdgesScreen
    ↓ (exceptions and overrides confirmed within Capabilities)
FlowsScreen (if multiple Archetypes exist in Scope)
    ↓ (Connectors and Bindings between Domains — how expertise flows)
SummaryScreen
    ↓ (complete Declaration displayed, export options)
```

### Screen Design Principles

1. **One thing at a time.** Each screen is a View — a filtered projection. Never show the full Declaration. Show one assertion in human language and ask for a response.

2. **Human language, not primitive language.** The person never sees "Capability" or "Archetype." They see "You evaluate carriers based on safety record, insurance coverage, and fleet age. Is that right?" The TML structure is invisible to the person being confirmed.

3. **Three responses everywhere.** Every assertion gets: Confirm (green), Correct (yellow), Flag for Discussion (blue). No other options.

4. **Progress is visible.** A persistent sidebar shows completion state across the Declaration — Archetypes confirmed, Domains confirmed, Capabilities confirmed, Policies confirmed, Skills referenced. Overall percentage.

5. **Corrections are natural language.** When someone chooses Correct, they get a text input. They rewrite the assertion in their own words. The system maps their correction back to the primitive structure. Every correction generates Provenance.

6. **Provenance is automatic.** Every confirmation, correction, and flag generates an immutable Provenance entry. The person never manages this. It happens.

### Widget Specifications

**AssertionWidget:**
- Displays a single assertion in a styled panel
- Assertion text is rendered as human-readable prose
- Source attribution shown in muted text below ("Extracted from: Confluence > Engineering Wiki > Carrier Evaluation Process")
- Confidence indicator (high/medium/low) shown as a subtle badge

**ResponseWidget:**
- Three buttons in a horizontal layout: Confirm | Correct | Flag
- Keyboard shortcuts: Enter = Confirm, E = Edit/Correct, F = Flag
- Visual feedback on selection (color change, brief animation)

**InlineEditorWidget:**
- Appears when Correct is selected
- Pre-populated with the current assertion text
- Standard text editing (multiline if needed)
- Submit with Ctrl+Enter, cancel with Escape

**ProgressSpineWidget:**
- Vertical sidebar (right side)
- Shows: Role [✓], Domains [3/5], Logic [1/3], Exceptions [0/2]
- Overall completion percentage
- Current position highlighted

### Textual-Web Serving

The same application can be served via `textual-web` for browser access:

```bash
# Local TUI
tml-engine confirm --source confluence --space "Engineering Wiki"

# Web-served (same app, accessible via browser)
tml-engine serve --port 8080
```

No code changes between modes. The Textual framework handles the rendering surface swap.

---

## 7. Storage

### SQLite Schema (Local)

```sql
-- Human identities (anchored to Workspace)
CREATE TABLE identities (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    title TEXT,
    department TEXT,
    workspace_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Extraction sessions
CREATE TABLE extractions (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_identifier TEXT NOT NULL,
    status TEXT DEFAULT 'in_progress',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- TML Primitives (polymorphic storage — all nine primitive types)
CREATE TABLE primitives (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,  -- scope, domain, capability, view, archetype, policy, connector, binding, provenance
    scope_id TEXT,  -- Every primitive MUST declare its Scope (except Scope itself for root)
    identity_id TEXT REFERENCES identities(id),
    extraction_id TEXT REFERENCES extractions(id),
    data JSON NOT NULL,  -- Full Pydantic model serialized
    confirmation_status TEXT DEFAULT 'unconfirmed',
    confirmed_by TEXT,
    confirmed_at TIMESTAMP,
    original_data JSON,  -- Pre-correction snapshot (for Provenance)
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Provenance (immutable, append-only — separate from polymorphic storage)
CREATE TABLE provenance (
    id TEXT PRIMARY KEY,
    scope_id TEXT NOT NULL,
    primitive_id TEXT NOT NULL REFERENCES primitives(id),
    primitive_type TEXT NOT NULL,
    action TEXT NOT NULL,  -- extracted, structured, confirmed, corrected, flagged
    actor_identity_id TEXT NOT NULL REFERENCES identities(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSON,
    previous_state JSON
);

-- Declarations (versioned snapshots of complete confirmed architectures)
CREATE TABLE declarations (
    id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    data JSON NOT NULL,  -- Full Declaration serialized
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completion_percentage REAL DEFAULT 0.0
);

-- Interview state (for pause/resume)
CREATE TABLE interview_sessions (
    id TEXT PRIMARY KEY,
    identity_id TEXT REFERENCES identities(id),
    phase TEXT NOT NULL,
    conversation_history JSON,
    discovered_primitives JSON,
    status TEXT DEFAULT 'in_progress',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP
);
```

---

## 8. CLI Interface

```bash
# Initialize a new project (creates SQLite DB, root Scope)
tml-engine init

# --- Core Extractors (ship with engine) ---

# Extract from a website
tml-engine extract web --url "https://example.com" --template default

# Run an adaptive interview
tml-engine interview --identity "user@company.com"

# Run an adaptive interview that fills gaps from prior extraction
tml-engine interview --identity "user@company.com" --fill-gaps

# --- Confirmation + Export ---

# Launch the confirmation surface
tml-engine confirm --identity "user@company.com"

# Serve the confirmation surface via web browser
tml-engine serve --port 8080

# Export a confirmed Declaration
tml-engine export --identity "user@company.com" --format json --output declaration.json
tml-engine export --identity "user@company.com" --format yaml --output declaration.yaml

# Export the organizational graph (when multiple Declarations exist)
tml-engine graph --scope "org-scope-id" --format json --output org-graph.json
tml-engine graph --scope "org-scope-id" --show-flows  # Print decision flows
tml-engine graph --scope "org-scope-id" --show-automation  # Print automation candidates

# Show status (primitives confirmed vs unconfirmed, Declarations complete)
tml-engine status

# --- Integration Plugins (available when installed) ---

# Extract from Atlassian (interactive source selection, requires plugin)
tml-engine extract atlassian
```

---

## 9. Sequencing (What Gets Built When)

### Stage 1: Foundation (Build First)
- [ ] Project scaffolding (pyproject.toml, src layout)
- [ ] TML Primitive data models (all nine primitives as Pydantic)
- [ ] Declaration model
- [ ] OrganizationalGraph, DecisionFlow, Dependency, AutomationCandidate models
- [ ] SQLite storage layer (with Provenance table)
- [ ] CLI skeleton with Click or Typer

### Stage 2: Confirmation Surface (Build Second)
- [ ] Textual application shell
- [ ] WelcomeScreen (Scope + Archetype identity establishment)
- [ ] ArchetypeScreen with Confirm/Correct/Flag
- [ ] DomainsScreen
- [ ] CapabilitiesScreen (per Domain — decision logic, heuristics, anti-patterns)
- [ ] SkillsScreen (per Capability — skill association and referencing)
- [ ] PoliciesScreen (constraints and guardrails)
- [ ] EdgesScreen (exceptions within Capabilities)
- [ ] FlowsScreen (Connectors + Bindings — only when multiple Archetypes exist)
- [ ] SummaryScreen (complete Declaration view + export)
- [ ] ProgressSpineWidget (tracks all nine primitive types)
- [ ] Mock data for testing the flow — use Michael's own expertise at Conversion
- [ ] Provenance generation on every confirmation/correction/flag

### Stage 3: Core Extractors (Build Third)
- [ ] BaseExtractor interface
- [ ] Web scrape extractor + default template
- [ ] LLM structurer (raw content → nine TML primitives via Claude)
- [ ] Scope assignment enforcement (every primitive MUST declare Scope)
- [ ] Provenance emission for every extraction and structuring action

### Stage 4: Adaptive Interview (Build Fourth)
- [ ] Interview engine with Claude API
- [ ] Five-phase interview flow (Scope → Archetype → Domains → Capabilities → Policies/Flows)
- [ ] Gap detection: compare existing primitives to interview targets
- [ ] Skill association phase: "What tools/processes do you use?"
- [ ] Policy extraction: "What rules can you never break?"
- [ ] Flow discovery: "Whose output do you depend on? Who depends on yours?"
- [ ] Pause/resume with SQLite persistence
- [ ] Interview inside the Textual TUI

### Stage 5: Identity + Distribution + Organizational Graph (Build Fifth)
- [ ] Pluggable identity provider interface (Google Workspace as first implementation)
- [ ] textual-web for browser-served confirmation surface
- [ ] Declaration versioning and export (JSON, YAML)
- [ ] OrganizationalGraph computation from multiple Declarations
- [ ] DecisionFlow tracing (Archetype → Binding → Connector → Archetype)
- [ ] Dependency mapping across Capabilities
- [ ] AutomationCandidate scoring (based on Capability completeness + Skills)
- [ ] PyPI packaging and distribution

### Stage 6: Integration Plugins (Build As Needed)
- [ ] Atlassian extractor (Confluence + Jira via MCP) — first plugin, Conversion case study
- [ ] Additional extractors as needed: Notion, SharePoint, Google Docs, etc.
- [ ] Additional identity providers: Microsoft 365, Okta, etc.

---

## 10. Claude Code Setup

### CLAUDE.md (Create This First)

```markdown
# TML Coherence Engine

## What This Is
A Python tool that extracts human expertise from multiple sources (web, interviews,
and pluggable integrations), structures it as TML primitive instances (the nine
primitives in the 3×3 grid), and presents a Textual TUI confirmation surface where
humans validate the extracted representation. Output is a Declaration — the versioned,
validated, diffable root of trust. Multiple Declarations compose into an
OrganizationalGraph. The core engine ships with two extractors that require zero
system access: the adaptive interview and the web scraper. Integration extractors
(Atlassian, Notion, SharePoint, etc.) are plugins built after the core is working.

## TML Primitives (the nine, closed set)
```
          Context        Control        Interaction
Boundary  Scope          View           Connector
Commit    Domain         Archetype      Binding
Truth     Capability     Policy         Provenance
```
Every primitive MUST declare its Scope. Provenance is emitted for all significant
actions. The Declaration is the root of trust.

## Stack
- Python 3.11+, Textual (latest), Pydantic v2, httpx, beautifulsoup4
- Anthropic Python SDK for LLM structuring and adaptive interviews
- SQLite for local storage (with dedicated Provenance table)
- Click or Typer for CLI
- Integration plugins (optional): Atlassian MCP, Google Workspace identity, etc.

## Project Structure
- src/tml_engine/ — all source code
- src/tml_engine/models/ — Pydantic data models for all nine primitives + Declaration + OrganizationalGraph
- src/tml_engine/extractors/ — core extractors (web, interview) + base interface
- src/tml_engine/extractors/plugins/ — integration extractors (atlassian, etc.)
- src/tml_engine/structurer/ — raw content → TML primitives via Claude
- src/tml_engine/confirmation/ — Textual TUI application (each screen is a View)
- src/tml_engine/storage/ — SQLite persistence
- src/tml_engine/graph/ — OrganizationalGraph computation
- tests/ — pytest test suite

## Code Style
- Type hints everywhere
- Async where I/O is involved
- Pydantic v2 for all data models
- No unnecessary abstractions — build what's needed now
- Docstrings on public functions, not on obvious ones

## How to Verify
- `pytest` for tests
- `python -m tml_engine.cli` to run the app
- `textual run src/tml_engine/confirmation/app.py` for TUI development

## Key Conventions
- TML primitives are always Pydantic models, never dicts
- Every primitive MUST have a scope_id (except the root Scope)
- Confirmation status is tracked at the primitive level
- Every confirmation/correction/flag generates Provenance
- Human-readable text is generated from primitives, never shown as schema
- The confirmation surface presents one assertion at a time
- All extractors produce RawExtractionResult, never primitives directly
- The structurer produces primitive instances, never raw content
- Capabilities contain DecisionFactors, ExceptionRules, and SkillReferences
- A Declaration is the complete confirmed architecture for a Scope
- OrganizationalGraph is computed from multiple Declarations, not stored directly
```

### Workflow

1. **Start Claude Code in the project directory**
2. **Set effort to max:** `CLAUDE_CODE_EFFORT_LEVEL=max`
3. **Use plan mode** (Shift+Tab twice) before each stage to review approach
4. **Build in stage order** — Foundation → Confirmation → Extractors → Interview → Distribution
5. **Test each stage** before moving to the next
6. **Use `/clear` between stages** to keep context focused

### First Prompt to Claude Code

```
Read SPEC.md and CLAUDE.md. We're building the TML Coherence Engine.

Start with Stage 1 (Foundation): scaffold the project, create the Pydantic
data models from the spec, set up SQLite storage, and create the CLI skeleton.

Use plan mode first to confirm your approach before writing any code.
After Stage 1 is complete and tests pass, we'll move to Stage 2.
```

---

## 11. Design Decisions and Rationale

**Why the nine TML primitives instead of custom data models?**
The Coherence Engine IS a TML implementation. It doesn't invent its own data model and then "map" to TML later. Every extracted, structured, and confirmed piece of expertise is born as a TML primitive instance. This means the output is immediately conformant, immediately composable with any other TML-conformant system, and immediately resolvable by agents that understand the Declaration format. Custom models would create a translation layer that adds complexity and loses fidelity.

**Why Capabilities contain decision logic, exceptions, AND skill references?**
In TML, Capability is the atomic unit of value — the locus of logic. It's where expertise actually lives. Decision factors, heuristics, anti-patterns, and exceptions are internal structure within a Capability, not separate primitives. Similarly, Skills are execution artifacts that Capabilities reference. The Capability says "I evaluate carriers based on safety record, insurance, and fleet age" (the logic) AND "I use this tool to pull the data" (the skill). Separating them would break the principle that Capability is the truth primitive for its column.

**Why the Declaration is the export format, not individual primitives?**
The Declaration is the versioned root of trust. Individual primitives are meaningless without their relationships, their Scope, and their Provenance. Exporting a single Capability without its Domain, its governing Policies, and its Scope context produces an orphan. The Declaration is the minimum viable unit of exchange.

**Why OrganizationalGraph is computed, not stored?**
The graph is a projection — a View across multiple Declarations. Storing it separately would create a second source of truth that can drift. Instead, the graph is computed fresh from the current state of all Declarations within a Scope tree. This is consistent with TML's principle that Views are projections, not independent data.

**Why Textual over a web framework?**
The confirmation surface is fundamentally sequential. A TUI is the purest expression of one-thing-at-a-time flow. Textual-web gives browser access without a rewrite.

**Why SQLite over PostgreSQL?**
This is a tool that runs locally first. SQLite is zero-config, portable, and sufficient. The schema is simple enough that migration to any backend is straightforward later.

**Why Pydantic over dataclasses?**
Validation, serialization, and JSON Schema generation built in. The primitives need to be transmitted, stored, and validated — Pydantic handles all three.

**Why core engine ships with only interview + web scrape?**
These two extractors require zero system access, zero credentials, zero organizational buy-in. Anyone can run the interview on themselves in 45 minutes. Anyone can point the scraper at a public website. This makes the core engine universally useful on first contact. Integration extractors (Atlassian, Notion, SharePoint) are plugins that unlock more value but require organizational access — they earn their way in after the core proves itself.

**Why MCP for the Atlassian plugin instead of direct API?**
MCP provides authenticated access through the user's existing Atlassian connection. No OAuth flow to build, no credentials to manage. The MCP server handles it. This pattern applies to future integration plugins as well — prefer MCP where available.

**Why pluggable identity instead of hard-coded Google Workspace?**
Google Workspace is the first implementation because it's what Conversion uses and it covers a large segment of the market. But Microsoft 365 shops, Okta-managed orgs, and others need the same engine. The identity provider is an interface — HumanIdentity is the model, Google Workspace is the first resolver. Same pattern as extractors.

**Why the structurer is separate from extractors?**
Extractors produce raw content. The structurer (LLM) produces structured primitives. Keeping them separate means: (a) you can swap LLM providers without touching extractors, (b) you can re-structure the same raw content with different prompts, (c) extraction is deterministic and cacheable while structuring is not.

**Why confirmation is not a separate phase from extraction?**
This is the core product insight. The primitives are immediately presented for confirmation after extraction. There is no intermediate state where unconfirmed primitives sit in a repository. The flow is: extract → structure → confirm → operational. This is one continuous motion. Every confirmation generates Provenance. The Declaration is born operational.
