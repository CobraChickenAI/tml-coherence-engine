"""OrganizationalGraph computation from Declarations.

Computes DecisionFlows, Dependencies, and AutomationCandidates by analyzing
Bindings, Connectors, and Capability completeness across multiple Declarations.
"""

from __future__ import annotations

from tml_engine.models.declaration import Declaration
from tml_engine.models.graph import (
    AutomationCandidate,
    DecisionFlow,
    Dependency,
    OrganizationalGraph,
)
from tml_engine.models.identity import ConfirmationStatus
from tml_engine.models.primitives import Capability, Scope


def compute_organizational_graph(
    declarations: list[Declaration],
    root_scope: Scope | None = None,
) -> OrganizationalGraph:
    """Compute an OrganizationalGraph from multiple Declarations.

    Traces decision flows via Binding → Connector pairs, derives dependencies,
    and scores Capabilities for automation readiness.
    """
    if not declarations:
        raise ValueError("At least one Declaration is required")

    if root_scope is None:
        root_scope = declarations[0].scope

    flows = _trace_decision_flows(declarations)
    deps = _derive_dependencies(flows)
    candidates = _score_automation_candidates(declarations)

    return OrganizationalGraph(
        root_scope=root_scope,
        declarations=declarations,
        decision_flows=flows,
        dependency_map=deps,
        automation_candidates=candidates,
    )


def _trace_decision_flows(declarations: list[Declaration]) -> list[DecisionFlow]:
    """Trace decision flows by matching Bindings to Connectors.

    A flow exists when a Binding writes to a target that a Connector
    (in the same or another Declaration) reads from.
    """
    flows: list[DecisionFlow] = []

    # Match bindings to connectors across all declarations
    for decl_a in declarations:
        for binding in decl_a.bindings:
            for decl_b in declarations:
                for connector in decl_b.connectors:
                    if not _targets_match(binding.writes_to, connector.reads_from):
                        continue

                    from_arch_id = _find_archetype(decl_a)
                    to_arch_id = _find_archetype(decl_b)
                    if not from_arch_id or not to_arch_id:
                        continue

                    from_cap_id = _find_capability_near(decl_a, binding.writes_to)
                    to_cap_id = _find_capability_near(decl_b, connector.reads_from)

                    flows.append(
                        DecisionFlow(
                            from_archetype_id=from_arch_id,
                            from_capability_id=from_cap_id or "",
                            to_archetype_id=to_arch_id,
                            to_capability_id=to_cap_id or "",
                            via_binding_id=binding.id,
                            via_connector_id=connector.id,
                            description=(
                                f"{binding.name} → {connector.name}: {binding.description}"
                            ),
                        )
                    )

    return flows


def _targets_match(writes_to: str, reads_from: str) -> bool:
    """Check if a Binding target matches a Connector source."""
    w = writes_to.lower().strip()
    r = reads_from.lower().strip()
    return w == r or w in r or r in w


def _find_archetype(decl: Declaration) -> str | None:
    return decl.archetypes[0].id if decl.archetypes else None


def _find_capability_near(decl: Declaration, target: str) -> str | None:
    """Find a capability related to the target string by name matching."""
    target_lower = target.lower()
    for cap in decl.capabilities:
        if target_lower in cap.name.lower() or cap.name.lower() in target_lower:
            return cap.id
    return decl.capabilities[0].id if decl.capabilities else None


def _derive_dependencies(flows: list[DecisionFlow]) -> list[Dependency]:
    """Derive dependency relationships from decision flows."""
    deps: list[Dependency] = []
    seen: set[tuple[str, str]] = set()

    for flow in flows:
        if not flow.from_capability_id or not flow.to_capability_id:
            continue

        key = (flow.from_capability_id, flow.to_capability_id)
        if key in seen:
            continue
        seen.add(key)

        deps.append(
            Dependency(
                upstream_capability_id=flow.from_capability_id,
                downstream_capability_id=flow.to_capability_id,
                dependency_type=_classify_dependency(flow.description),
                description=flow.description,
            )
        )

    return deps


_BLOCKING_KEYWORDS = {
    "must",
    "requires",
    "blocks",
    "blocking",
    "required",
    "depends on",
    "prerequisite",
}
_GATING_KEYWORDS = {"gates", "approves", "approval", "authorize", "gating", "review"}


def _classify_dependency(description: str) -> str:
    """Classify a dependency type based on description keywords."""
    lower = description.lower()
    for kw in _BLOCKING_KEYWORDS:
        if kw in lower:
            return "blocking"
    for kw in _GATING_KEYWORDS:
        if kw in lower:
            return "gating"
    return "informing"


def _score_automation_candidates(
    declarations: list[Declaration],
) -> list[AutomationCandidate]:
    """Score each Capability for automation readiness.

    Scoring (0.0 to 1.0 total):
    - Decision factors with weights: +0.2
    - Heuristics populated: +0.2
    - Exceptions documented: +0.15
    - Automatable skills: +0.2
    - Anti-patterns documented: +0.1
    - Confirmed status: +0.15
    """
    candidates: list[AutomationCandidate] = []

    for decl in declarations:
        domain_to_arch: dict[str, str] = {d.id: d.accountable_archetype_id for d in decl.domains}

        for cap in decl.capabilities:
            score, missing, rationale_parts = _score_capability(cap)
            arch_id = domain_to_arch.get(cap.domain_id, "")

            if score > 0.7:
                skill_type = "agent_skill"
            elif score > 0.4:
                skill_type = "workflow"
            else:
                skill_type = "copilot"

            candidates.append(
                AutomationCandidate(
                    capability_id=cap.id,
                    archetype_id=arch_id,
                    automation_readiness=round(score, 2),
                    missing_elements=missing,
                    recommended_skill_type=skill_type,
                    rationale="; ".join(rationale_parts),
                )
            )

    return candidates


def _score_capability(cap: Capability) -> tuple[float, list[str], list[str]]:
    """Score a single capability. Returns (score, missing_elements, rationale_parts)."""
    score = 0.0
    missing: list[str] = []
    rationale: list[str] = []

    # Decision factors with weights (+0.2)
    weighted_factors = [f for f in cap.decision_factors if f.weight]
    if weighted_factors:
        score += 0.2
        rationale.append(f"{len(weighted_factors)} weighted decision factors")
    else:
        missing.append("Decision factors with weights")

    # Heuristics (+0.2)
    if cap.heuristics:
        score += 0.2
        rationale.append(f"{len(cap.heuristics)} heuristics")
    else:
        missing.append("Heuristics (rules of thumb)")

    # Exceptions (+0.15)
    if cap.exceptions:
        score += 0.15
        rationale.append(f"{len(cap.exceptions)} exception rules documented")
    else:
        missing.append("Exception rules")

    # Automatable skills (+0.2)
    automatable_types = {"agent_skill", "tool", "workflow"}
    automatable_skills = [s for s in cap.skills if s.skill_type in automatable_types]
    if automatable_skills:
        score += 0.2
        rationale.append(f"{len(automatable_skills)} automatable skills")
    else:
        missing.append("Automatable skills (agent_skill, tool, or workflow)")

    # Anti-patterns (+0.1)
    if cap.anti_patterns:
        score += 0.1
        rationale.append(f"{len(cap.anti_patterns)} anti-patterns documented")
    else:
        missing.append("Anti-patterns")

    # Confirmation status (+0.15)
    if cap.confirmation and cap.confirmation.status in (
        ConfirmationStatus.CONFIRMED,
        ConfirmationStatus.CORRECTED,
    ):
        score += 0.15
        rationale.append("Confirmed by human")
    else:
        missing.append("Human confirmation")

    return score, missing, rationale
