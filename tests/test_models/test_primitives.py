"""Tests for TML primitive models."""

from datetime import UTC, datetime

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
    Policy,
    ProvenanceEntry,
    Scope,
    SkillReference,
    View,
)


def _make_identity() -> HumanIdentity:
    return HumanIdentity(email="michael@cobrachicken.ai", display_name="Michael")


def _make_source() -> ExtractionSource:
    return ExtractionSource(
        source_type="interview",
        source_identifier="session-001",
        extracted_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def _make_confirmation() -> ConfirmationRecord:
    return ConfirmationRecord(
        status=ConfirmationStatus.CONFIRMED,
        confirmed_by=_make_identity(),
        confirmed_at=datetime(2025, 1, 2, tzinfo=UTC),
    )


class TestScope:
    def test_create_root_scope(self) -> None:
        scope = Scope(
            id="scope-root",
            name="CobraChicken AI",
            description="Root organizational scope",
            owner_identity=_make_identity(),
            source=_make_source(),
        )
        assert scope.id == "scope-root"
        assert scope.parent_scope_id is None
        assert scope.confirmation is None

    def test_create_nested_scope(self) -> None:
        scope = Scope(
            id="scope-team",
            name="Engineering",
            description="Engineering team scope",
            parent_scope_id="scope-root",
            owner_identity=_make_identity(),
            source=_make_source(),
        )
        assert scope.parent_scope_id == "scope-root"

    def test_scope_with_confirmation(self) -> None:
        scope = Scope(
            id="scope-1",
            name="Test",
            description="Test scope",
            owner_identity=_make_identity(),
            confirmation=_make_confirmation(),
            source=_make_source(),
        )
        assert scope.confirmation is not None
        assert scope.confirmation.status == ConfirmationStatus.CONFIRMED


class TestDomain:
    def test_create_domain(self) -> None:
        domain = Domain(
            id="domain-1",
            scope_id="scope-root",
            name="Carrier Evaluation",
            description="Evaluating and selecting freight carriers",
            outcome_definition="Reliable, cost-effective carrier partnerships",
            accountable_archetype_id="arch-1",
            source=_make_source(),
        )
        assert domain.scope_id == "scope-root"
        assert domain.accountable_archetype_id == "arch-1"


class TestCapability:
    def test_create_capability_with_full_structure(self) -> None:
        cap = Capability(
            id="cap-1",
            scope_id="scope-root",
            domain_id="domain-1",
            name="Carrier Safety Assessment",
            description="Evaluate carrier safety record and compliance",
            outcome="Approved or rejected carrier based on safety criteria",
            decision_factors=[
                DecisionFactor(
                    name="Safety Score", description="DOT safety rating", weight="primary"
                ),
                DecisionFactor(name="Insurance Coverage", description="Liability limits"),
            ],
            heuristics=["Score below 70 is automatic reject", "Check last 3 years of incidents"],
            anti_patterns=["Ignoring recent incidents because historical score is good"],
            exceptions=[
                ExceptionRule(
                    trigger="Emergency load with no approved carriers available",
                    override_description="Allow provisional approval with enhanced monitoring",
                    reason="Business continuity requires flexibility in emergencies",
                ),
            ],
            skills=[
                SkillReference(
                    id="skill-1",
                    name="SaferSys Lookup",
                    description="Query FMCSA SaferSys for carrier data",
                    skill_type="tool",
                ),
            ],
            source=_make_source(),
        )
        assert len(cap.decision_factors) == 2
        assert len(cap.exceptions) == 1
        assert len(cap.skills) == 1
        assert cap.domain_id == "domain-1"

    def test_empty_capability(self) -> None:
        cap = Capability(
            id="cap-2",
            scope_id="scope-root",
            domain_id="domain-1",
            name="Minimal",
            description="Minimal capability",
            outcome="Outcome",
            decision_factors=[],
            heuristics=[],
            anti_patterns=[],
            exceptions=[],
            skills=[],
            source=_make_source(),
        )
        assert cap.decision_factors == []


class TestArchetype:
    def test_create_archetype(self) -> None:
        arch = Archetype(
            id="arch-1",
            scope_id="scope-root",
            identity=_make_identity(),
            role_name="Logistics Manager",
            role_description="Manages carrier relationships and freight operations",
            primary_responsibilities=["Carrier selection", "Rate negotiation"],
            decision_authority=["Approve carriers up to $500k annual spend"],
            accountability_boundaries=["Cannot approve international routes"],
            source=_make_source(),
        )
        assert arch.role_name == "Logistics Manager"
        assert len(arch.primary_responsibilities) == 2


class TestView:
    def test_create_view(self) -> None:
        view = View(
            id="view-1",
            scope_id="scope-root",
            name="Carrier Evaluation Confirmation",
            description="Confirmation view for carrier evaluation capabilities",
            capability_ids=["cap-1", "cap-2"],
            target_archetype_id="arch-1",
            projection_format="confirmation",
        )
        assert len(view.capability_ids) == 2
        assert view.projection_format == "confirmation"


class TestPolicy:
    def test_create_policy(self) -> None:
        policy = Policy(
            id="pol-1",
            scope_id="scope-root",
            name="Minimum Insurance Requirement",
            description="All carriers must carry minimum liability insurance",
            rule="Carrier must have at least $1M general liability coverage",
            attaches_to=["cap-1"],
            enforcement_level="hard",
            source=_make_source(),
        )
        assert policy.enforcement_level == "hard"
        assert "cap-1" in policy.attaches_to


class TestConnector:
    def test_create_connector(self) -> None:
        conn = Connector(
            id="conn-1",
            scope_id="scope-root",
            name="FMCSA Data Feed",
            reads_from="external-fmcsa",
            reads_from_type="external_system",
            governed_by_policy_ids=["pol-1"],
            description="Reads carrier safety data from FMCSA",
            source=_make_source(),
        )
        assert conn.reads_from_type == "external_system"


class TestBinding:
    def test_create_binding(self) -> None:
        binding = Binding(
            id="bind-1",
            scope_id="scope-root",
            name="Carrier Approval Notification",
            writes_to="cap-downstream",
            writes_to_type="capability",
            governed_by_policy_ids=["pol-1"],
            description="Notifies dispatch when carrier is approved",
            source=_make_source(),
        )
        assert binding.writes_to_type == "capability"


class TestProvenance:
    def test_create_provenance_entry(self) -> None:
        entry = ProvenanceEntry(
            id="prov-1",
            scope_id="scope-root",
            primitive_id="cap-1",
            primitive_type="capability",
            action="confirmed",
            actor=_make_identity(),
            timestamp=datetime(2025, 1, 2, tzinfo=UTC),
            details={"confirmation_status": "confirmed"},
        )
        assert entry.action == "confirmed"
        assert entry.previous_state is None

    def test_provenance_with_previous_state(self) -> None:
        entry = ProvenanceEntry(
            id="prov-2",
            scope_id="scope-root",
            primitive_id="cap-1",
            primitive_type="capability",
            action="corrected",
            actor=_make_identity(),
            timestamp=datetime(2025, 1, 3, tzinfo=UTC),
            details={"correction": "Updated heuristics"},
            previous_state={"heuristics": ["old rule"]},
        )
        assert entry.previous_state is not None


class TestSerialization:
    def test_scope_round_trip(self) -> None:
        scope = Scope(
            id="scope-1",
            name="Test",
            description="Test scope",
            owner_identity=_make_identity(),
            source=_make_source(),
        )
        data = scope.model_dump(mode="json")
        restored = Scope.model_validate(data)
        assert restored.id == scope.id
        assert restored.owner_identity.email == scope.owner_identity.email

    def test_capability_round_trip(self) -> None:
        cap = Capability(
            id="cap-1",
            scope_id="scope-root",
            domain_id="domain-1",
            name="Test Capability",
            description="A test",
            outcome="Test outcome",
            decision_factors=[DecisionFactor(name="Factor", description="Desc")],
            heuristics=["Rule 1"],
            anti_patterns=["Bad pattern"],
            exceptions=[],
            skills=[],
            source=_make_source(),
        )
        data = cap.model_dump(mode="json")
        restored = Capability.model_validate(data)
        assert restored.decision_factors[0].name == "Factor"
