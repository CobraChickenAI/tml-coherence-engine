"""Tests for OrganizationalGraph and related models."""

from datetime import UTC, datetime

from tml_engine.models.declaration import Declaration
from tml_engine.models.graph import (
    AutomationCandidate,
    DecisionFlow,
    Dependency,
    OrganizationalGraph,
)
from tml_engine.models.identity import ExtractionSource, HumanIdentity
from tml_engine.models.primitives import Scope


def _identity() -> HumanIdentity:
    return HumanIdentity(email="test@example.com", display_name="Test")


def _source() -> ExtractionSource:
    return ExtractionSource(
        source_type="interview",
        source_identifier="test",
        extracted_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def _scope() -> Scope:
    return Scope(
        id="scope-root",
        name="Root",
        description="Root scope",
        owner_identity=_identity(),
        source=_source(),
    )


def _declaration() -> Declaration:
    return Declaration(
        id="decl-1",
        version="0.1.0",
        scope=_scope(),
        archetypes=[],
        domains=[],
        capabilities=[],
        views=[],
        policies=[],
        connectors=[],
        bindings=[],
        provenance=[],
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


class TestDecisionFlow:
    def test_create(self) -> None:
        flow = DecisionFlow(
            from_archetype_id="arch-1",
            from_capability_id="cap-1",
            to_archetype_id="arch-2",
            to_capability_id="cap-3",
            via_binding_id="bind-1",
            via_connector_id="conn-1",
            description="Carrier approval triggers dispatch scheduling",
        )
        assert flow.from_archetype_id == "arch-1"
        assert flow.to_archetype_id == "arch-2"


class TestDependency:
    def test_create(self) -> None:
        dep = Dependency(
            upstream_capability_id="cap-1",
            downstream_capability_id="cap-2",
            dependency_type="blocking",
            description="Must evaluate carrier before scheduling",
        )
        assert dep.dependency_type == "blocking"


class TestAutomationCandidate:
    def test_create(self) -> None:
        candidate = AutomationCandidate(
            capability_id="cap-1",
            archetype_id="arch-1",
            automation_readiness=0.85,
            missing_elements=["Exception handling for international routes"],
            recommended_skill_type="agent_skill",
            rationale="Decision factors are well-defined, few exceptions",
        )
        assert candidate.automation_readiness == 0.85
        assert len(candidate.missing_elements) == 1


class TestOrganizationalGraph:
    def test_create_empty(self) -> None:
        graph = OrganizationalGraph(
            root_scope=_scope(),
            declarations=[_declaration()],
            decision_flows=[],
            dependency_map=[],
            automation_candidates=[],
        )
        assert len(graph.declarations) == 1

    def test_serialization_round_trip(self) -> None:
        graph = OrganizationalGraph(
            root_scope=_scope(),
            declarations=[_declaration()],
            decision_flows=[
                DecisionFlow(
                    from_archetype_id="a1",
                    from_capability_id="c1",
                    to_archetype_id="a2",
                    to_capability_id="c2",
                    via_binding_id="b1",
                    via_connector_id="cn1",
                    description="Test flow",
                ),
            ],
            dependency_map=[],
            automation_candidates=[],
        )
        data = graph.model_dump(mode="json")
        restored = OrganizationalGraph.model_validate(data)
        assert len(restored.decision_flows) == 1
