"""OrganizationalGraph — composed view across multiple Declarations."""

from __future__ import annotations

from pydantic import BaseModel

from tml_engine.models.declaration import Declaration
from tml_engine.models.primitives import Scope


class DecisionFlow(BaseModel):
    """Traced path showing how a decision in one Archetype's Domain
    cascades to affect another Archetype's Domain."""

    from_archetype_id: str
    from_capability_id: str
    to_archetype_id: str
    to_capability_id: str
    via_binding_id: str
    via_connector_id: str
    description: str


class Dependency(BaseModel):
    """Explicit dependency between Capabilities across Archetypes."""

    upstream_capability_id: str
    downstream_capability_id: str
    dependency_type: str  # "blocking", "informing", "gating"
    description: str


class AutomationCandidate(BaseModel):
    """A Capability where confirmed decision logic + skills suggest
    an agent could handle it."""

    capability_id: str
    archetype_id: str
    automation_readiness: float  # 0.0 to 1.0
    missing_elements: list[str]
    recommended_skill_type: str  # "agent_skill", "workflow", "copilot"
    rationale: str


class OrganizationalGraph(BaseModel):
    """Composed view across multiple Declarations within nested Scopes.
    Computed from Declarations, never stored separately."""

    root_scope: Scope
    declarations: list[Declaration]
    decision_flows: list[DecisionFlow]
    dependency_map: list[Dependency]
    automation_candidates: list[AutomationCandidate]
