"""Tests for OrganizationalGraph computation."""

from datetime import UTC, datetime

import pytest

from tml_engine.graph.compute import (
    _classify_dependency,
    _score_capability,
    _targets_match,
    _trace_decision_flows,
    compute_organizational_graph,
)
from tml_engine.models.declaration import Declaration
from tml_engine.models.identity import (
    ConfirmationRecord,
    ConfirmationStatus,
    ExtractionSource,
    HumanIdentity,
)
from tml_engine.models.primitives import (
    Archetype,
    Binding,
    Capability,
    Connector,
    DecisionFactor,
    Domain,
    ExceptionRule,
    Scope,
    SkillReference,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _identity() -> HumanIdentity:
    return HumanIdentity(email="test@example.com", display_name="Test User")


def _source() -> ExtractionSource:
    return ExtractionSource(source_type="test", source_identifier="test", extracted_at=_now())


def _scope(scope_id: str = "scope-1") -> Scope:
    return Scope(
        id=scope_id,
        name="Test Scope",
        description="Test",
        owner_identity=_identity(),
        source=_source(),
    )


def _declaration(
    scope_id: str = "scope-1",
    archetypes: list | None = None,
    domains: list | None = None,
    capabilities: list | None = None,
    connectors: list | None = None,
    bindings: list | None = None,
    policies: list | None = None,
) -> Declaration:
    return Declaration(
        id=f"decl-{scope_id}",
        version="0.1.0",
        scope=_scope(scope_id),
        archetypes=archetypes or [],
        domains=domains or [],
        capabilities=capabilities or [],
        views=[],
        policies=policies or [],
        connectors=connectors or [],
        bindings=bindings or [],
        provenance=[],
        created_at=_now(),
    )


def _archetype(arch_id: str = "arch-1", scope_id: str = "scope-1") -> Archetype:
    return Archetype(
        id=arch_id,
        scope_id=scope_id,
        identity=_identity(),
        role_name="Test Role",
        role_description="Test",
        primary_responsibilities=["Test"],
        decision_authority=["Test"],
        accountability_boundaries=["Test"],
        source=_source(),
    )


def _domain(dom_id: str = "dom-1", scope_id: str = "scope-1", arch_id: str = "arch-1") -> Domain:
    return Domain(
        id=dom_id,
        scope_id=scope_id,
        name="Test Domain",
        description="Test",
        outcome_definition="Success",
        accountable_archetype_id=arch_id,
        source=_source(),
    )


def _capability(
    cap_id: str = "cap-1",
    scope_id: str = "scope-1",
    domain_id: str = "dom-1",
    *,
    with_factors: bool = True,
    with_heuristics: bool = True,
    with_anti_patterns: bool = True,
    with_exceptions: bool = False,
    with_skills: bool = True,
    confirmed: bool = False,
) -> Capability:
    factors = (
        [DecisionFactor(name="F1", description="Factor", weight="primary")] if with_factors else []
    )
    heuristics = ["Rule of thumb"] if with_heuristics else []
    anti_patterns = ["Bad practice"] if with_anti_patterns else []
    exceptions = (
        [ExceptionRule(trigger="Edge case", override_description="Override", reason="Reason")]
        if with_exceptions
        else []
    )
    skills = (
        [SkillReference(id="sk-1", name="Tool", description="A tool", skill_type="tool")]
        if with_skills
        else []
    )
    confirmation = (
        ConfirmationRecord(
            status=ConfirmationStatus.CONFIRMED,
            confirmed_by=_identity(),
            confirmed_at=_now(),
        )
        if confirmed
        else None
    )

    return Capability(
        id=cap_id,
        scope_id=scope_id,
        domain_id=domain_id,
        name="Test Capability",
        description="Test",
        outcome="Good outcome",
        decision_factors=factors,
        heuristics=heuristics,
        anti_patterns=anti_patterns,
        exceptions=exceptions,
        skills=skills,
        confirmation=confirmation,
        source=_source(),
    )


class TestTargetsMatch:
    def test_exact_match(self) -> None:
        assert _targets_match("Dispatch Team", "Dispatch Team")

    def test_case_insensitive(self) -> None:
        assert _targets_match("dispatch team", "Dispatch Team")

    def test_substring_match(self) -> None:
        assert _targets_match("Dispatch", "Dispatch Team Queue")

    def test_no_match(self) -> None:
        assert not _targets_match("Sales", "Engineering")


class TestClassifyDependency:
    def test_blocking(self) -> None:
        assert _classify_dependency("This requires approval before proceeding") == "blocking"

    def test_gating(self) -> None:
        assert _classify_dependency("Manager approval gates the release") == "gating"

    def test_informing_default(self) -> None:
        assert _classify_dependency("Status update sent downstream") == "informing"

    def test_informing_explicit(self) -> None:
        assert _classify_dependency("This informs the next step") == "informing"


class TestDecisionFlowTracing:
    def test_matching_binding_connector(self) -> None:
        decl = _declaration(
            archetypes=[_archetype()],
            domains=[_domain()],
            capabilities=[_capability()],
            bindings=[
                Binding(
                    id="bind-1",
                    scope_id="scope-1",
                    name="Output → Downstream",
                    writes_to="Dispatch Team",
                    writes_to_type="external_system",
                    governed_by_policy_ids=[],
                    description="Send to dispatch",
                    source=_source(),
                ),
            ],
            connectors=[
                Connector(
                    id="conn-1",
                    scope_id="scope-1",
                    name="Upstream → Input",
                    reads_from="Dispatch Team",
                    reads_from_type="external_system",
                    governed_by_policy_ids=[],
                    description="Receive from dispatch",
                    source=_source(),
                ),
            ],
        )
        flows = _trace_decision_flows([decl])
        assert len(flows) == 1
        assert flows[0].via_binding_id == "bind-1"
        assert flows[0].via_connector_id == "conn-1"

    def test_no_matching_flows(self) -> None:
        decl = _declaration(
            archetypes=[_archetype()],
            bindings=[
                Binding(
                    id="bind-1",
                    scope_id="scope-1",
                    name="Out",
                    writes_to="Alpha",
                    writes_to_type="external_system",
                    governed_by_policy_ids=[],
                    description="To alpha",
                    source=_source(),
                ),
            ],
            connectors=[
                Connector(
                    id="conn-1",
                    scope_id="scope-1",
                    name="In",
                    reads_from="Beta",
                    reads_from_type="external_system",
                    governed_by_policy_ids=[],
                    description="From beta",
                    source=_source(),
                ),
            ],
        )
        flows = _trace_decision_flows([decl])
        assert len(flows) == 0


class TestScoreCapability:
    def test_full_score(self) -> None:
        cap = _capability(
            with_factors=True,
            with_heuristics=True,
            with_anti_patterns=True,
            with_exceptions=True,
            with_skills=True,
            confirmed=True,
        )
        score, missing, rationale = _score_capability(cap)
        assert score == 1.0
        assert missing == []
        assert len(rationale) == 6

    def test_empty_capability(self) -> None:
        cap = _capability(
            with_factors=False,
            with_heuristics=False,
            with_anti_patterns=False,
            with_exceptions=False,
            with_skills=False,
            confirmed=False,
        )
        score, missing, rationale = _score_capability(cap)
        assert score == 0.0
        assert len(missing) == 6
        assert rationale == []

    def test_partial_score(self) -> None:
        cap = _capability(
            with_factors=True,
            with_heuristics=True,
            with_anti_patterns=False,
            with_exceptions=False,
            with_skills=False,
            confirmed=False,
        )
        score, missing, _rationale = _score_capability(cap)
        assert score == pytest.approx(0.4)
        assert "Anti-patterns" in missing
        assert "Exception rules" in missing


class TestComputeOrganizationalGraph:
    def test_empty_declarations_raises(self) -> None:
        with pytest.raises(ValueError, match="At least one Declaration"):
            compute_organizational_graph([])

    def test_single_declaration(self) -> None:
        decl = _declaration(
            archetypes=[_archetype()],
            domains=[_domain()],
            capabilities=[_capability()],
        )
        graph = compute_organizational_graph([decl])
        assert graph.root_scope.id == "scope-1"
        assert len(graph.declarations) == 1
        assert len(graph.automation_candidates) == 1

    def test_automation_candidate_scoring(self) -> None:
        cap = _capability(
            with_factors=True,
            with_heuristics=True,
            with_anti_patterns=True,
            with_exceptions=True,
            with_skills=True,
            confirmed=True,
        )
        decl = _declaration(
            archetypes=[_archetype()],
            domains=[_domain()],
            capabilities=[cap],
        )
        graph = compute_organizational_graph([decl])
        assert len(graph.automation_candidates) == 1
        candidate = graph.automation_candidates[0]
        assert candidate.automation_readiness == 1.0
        assert candidate.recommended_skill_type == "agent_skill"
        assert candidate.missing_elements == []

    def test_low_readiness_copilot(self) -> None:
        cap = _capability(
            with_factors=False,
            with_heuristics=False,
            with_anti_patterns=False,
            with_exceptions=False,
            with_skills=False,
            confirmed=False,
        )
        decl = _declaration(
            archetypes=[_archetype()],
            domains=[_domain()],
            capabilities=[cap],
        )
        graph = compute_organizational_graph([decl])
        candidate = graph.automation_candidates[0]
        assert candidate.automation_readiness == 0.0
        assert candidate.recommended_skill_type == "copilot"

    def test_cross_declaration_flows(self) -> None:
        decl_a = _declaration(
            scope_id="scope-a",
            archetypes=[_archetype("arch-a", "scope-a")],
            domains=[_domain("dom-a", "scope-a", "arch-a")],
            capabilities=[_capability("cap-a", "scope-a", "dom-a")],
            bindings=[
                Binding(
                    id="bind-a",
                    scope_id="scope-a",
                    name="Output",
                    writes_to="Shared Queue",
                    writes_to_type="external_system",
                    governed_by_policy_ids=[],
                    description="Send to shared queue",
                    source=_source(),
                ),
            ],
        )
        decl_b = _declaration(
            scope_id="scope-b",
            archetypes=[_archetype("arch-b", "scope-b")],
            domains=[_domain("dom-b", "scope-b", "arch-b")],
            capabilities=[_capability("cap-b", "scope-b", "dom-b")],
            connectors=[
                Connector(
                    id="conn-b",
                    scope_id="scope-b",
                    name="Input",
                    reads_from="Shared Queue",
                    reads_from_type="external_system",
                    governed_by_policy_ids=[],
                    description="Read from shared queue",
                    source=_source(),
                ),
            ],
        )
        graph = compute_organizational_graph([decl_a, decl_b], root_scope=_scope("root"))
        assert len(graph.decision_flows) == 1
        assert graph.decision_flows[0].from_archetype_id == "arch-a"
        assert graph.decision_flows[0].to_archetype_id == "arch-b"
        assert len(graph.dependency_map) == 1
