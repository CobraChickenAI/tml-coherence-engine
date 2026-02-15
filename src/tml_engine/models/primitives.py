"""All nine TML primitive Pydantic models.

The nine primitives form a closed 3x3 grid:

              Context        Control        Interaction
    Boundary  Scope          View           Connector
    Commit    Domain         Archetype      Binding
    Truth     Capability     Policy         Provenance

Every primitive MUST declare its Scope (except the root Scope itself).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from tml_engine.models.identity import (
    ConfirmationRecord,
    ExtractionSource,
    HumanIdentity,
)

# ---------------------------------------------------------------------------
# Internal structures (not TML primitives — sub-components of Capability)
# ---------------------------------------------------------------------------


class DecisionFactor(BaseModel):
    """A factor within a Capability's decision logic."""

    name: str
    description: str
    weight: str | None = None  # "primary", "secondary", "tiebreaker"
    confirmation: ConfirmationRecord | None = None


class ExceptionRule(BaseModel):
    """Edge cases and overrides within a Capability. Pure tacit knowledge."""

    trigger: str  # What condition activates this exception
    override_description: str  # What happens when the exception fires
    reason: str  # Why this exception exists
    confirmation: ConfirmationRecord | None = None


class SkillReference(BaseModel):
    """Reference to an executable skill that operationalizes a Capability.
    Bridge to SkillPack and agent execution."""

    id: str
    name: str
    description: str
    skill_type: str  # "agent_skill", "workflow", "tool", "process", "manual"
    execution_surface: str | None = None
    skill_uri: str | None = None
    confirmation: ConfirmationRecord | None = None


# ---------------------------------------------------------------------------
# Context Primitives — Where Things Live
# ---------------------------------------------------------------------------


class Scope(BaseModel):
    """Bounded organizational or ownership context.
    Every other primitive instance MUST declare its Scope.
    Scopes MAY be nested."""

    id: str
    name: str
    description: str
    parent_scope_id: str | None = None
    owner_identity: HumanIdentity
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


class Domain(BaseModel):
    """Outcome-based accountability boundary for a functional area.
    A Domain MUST own at least one Capability and MUST declare its Scope."""

    id: str
    scope_id: str
    name: str
    description: str
    outcome_definition: str
    accountable_archetype_id: str
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


class Capability(BaseModel):
    """The atomic unit of value — locus of logic.
    Contains decision factors, heuristics, anti-patterns, exceptions, and skill references.
    MUST belong to exactly one Domain and MUST declare its Scope."""

    id: str
    scope_id: str
    domain_id: str
    name: str
    description: str
    outcome: str
    decision_factors: list[DecisionFactor]
    heuristics: list[str]
    anti_patterns: list[str]
    exceptions: list[ExceptionRule]
    skills: list[SkillReference]
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


# ---------------------------------------------------------------------------
# Control Primitives — How It Is Constrained
# ---------------------------------------------------------------------------


class View(BaseModel):
    """Filtered projection of Capabilities for a specific caller.
    MUST reference at least one Capability. MUST declare its Scope."""

    id: str
    scope_id: str
    name: str
    description: str
    capability_ids: list[str]
    target_archetype_id: str | None = None
    projection_format: str  # "confirmation", "summary", "operational", "export"


class Archetype(BaseModel):
    """Caller role definition constraining what actions a caller may take.
    MUST declare its Scope."""

    id: str
    scope_id: str
    identity: HumanIdentity
    role_name: str
    role_description: str
    primary_responsibilities: list[str]
    decision_authority: list[str]
    accountability_boundaries: list[str]
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


class Policy(BaseModel):
    """Enforced rule or constraint governing one or more primitives.
    Deny by default. MUST declare its Scope and the primitives it attaches to."""

    id: str
    scope_id: str
    name: str
    description: str
    rule: str
    attaches_to: list[str]
    enforcement_level: str  # "hard" (never violated), "soft" (overridable with reason)
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


# ---------------------------------------------------------------------------
# Interaction Primitives — How It Crosses Boundaries
# ---------------------------------------------------------------------------


class Connector(BaseModel):
    """Governed read access pathway across Scopes or Domains.
    Represents how expertise flows INTO a domain."""

    id: str
    scope_id: str
    name: str
    reads_from: str
    reads_from_type: str  # "capability", "domain", "external_system"
    governed_by_policy_ids: list[str]
    description: str
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


class Binding(BaseModel):
    """Governed write access link that commits effects.
    Represents how expertise flows OUT of a domain."""

    id: str
    scope_id: str
    name: str
    writes_to: str
    writes_to_type: str  # "capability", "domain", "external_system"
    governed_by_policy_ids: list[str]
    description: str
    confirmation: ConfirmationRecord | None = None
    source: ExtractionSource


class ProvenanceEntry(BaseModel):
    """Immutable, append-only record of origin, change history, and ownership.
    MUST be emitted for all significant actions."""

    id: str
    scope_id: str
    primitive_id: str
    primitive_type: str
    action: str  # "extracted", "structured", "confirmed", "corrected", "flagged"
    actor: HumanIdentity
    timestamp: datetime
    details: dict
    previous_state: dict | None = None
