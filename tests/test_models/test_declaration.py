"""Tests for Declaration model."""

from datetime import UTC, datetime

from tml_engine.models.declaration import Declaration
from tml_engine.models.identity import (
    ConfirmationRecord,
    ConfirmationStatus,
    ExtractionSource,
    HumanIdentity,
)
from tml_engine.models.primitives import (
    Archetype,
    Capability,
    Domain,
    Scope,
)


def _identity() -> HumanIdentity:
    return HumanIdentity(email="test@example.com", display_name="Test User")


def _source() -> ExtractionSource:
    return ExtractionSource(
        source_type="interview",
        source_identifier="test-session",
        extracted_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def _confirmed() -> ConfirmationRecord:
    return ConfirmationRecord(
        status=ConfirmationStatus.CONFIRMED,
        confirmed_by=_identity(),
        confirmed_at=datetime(2025, 1, 2, tzinfo=UTC),
    )


def _make_declaration(
    *,
    scope_confirmed: bool = False,
    archetype_confirmed: bool = False,
    domain_confirmed: bool = False,
    cap_confirmed: bool = False,
) -> Declaration:
    scope = Scope(
        id="scope-1",
        name="Test Scope",
        description="Test",
        owner_identity=_identity(),
        confirmation=_confirmed() if scope_confirmed else None,
        source=_source(),
    )
    archetype = Archetype(
        id="arch-1",
        scope_id="scope-1",
        identity=_identity(),
        role_name="Tester",
        role_description="Tests things",
        primary_responsibilities=["Testing"],
        decision_authority=["Test decisions"],
        accountability_boundaries=["Only testing"],
        confirmation=_confirmed() if archetype_confirmed else None,
        source=_source(),
    )
    domain = Domain(
        id="domain-1",
        scope_id="scope-1",
        name="Testing Domain",
        description="Domain for testing",
        outcome_definition="All tests pass",
        accountable_archetype_id="arch-1",
        confirmation=_confirmed() if domain_confirmed else None,
        source=_source(),
    )
    capability = Capability(
        id="cap-1",
        scope_id="scope-1",
        domain_id="domain-1",
        name="Test Execution",
        description="Execute tests",
        outcome="Tests run",
        decision_factors=[],
        heuristics=[],
        anti_patterns=[],
        exceptions=[],
        skills=[],
        confirmation=_confirmed() if cap_confirmed else None,
        source=_source(),
    )
    return Declaration(
        id="decl-1",
        version="0.1.0",
        scope=scope,
        archetypes=[archetype],
        domains=[domain],
        capabilities=[capability],
        views=[],
        policies=[],
        connectors=[],
        bindings=[],
        provenance=[],
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


class TestDeclaration:
    def test_unconfirmed_declaration(self) -> None:
        decl = _make_declaration()
        assert decl.confirmed_count() == 0
        assert decl.unconfirmed_count() == 4  # scope + archetype + domain + capability
        assert decl.total_confirmable() == 4

    def test_partially_confirmed(self) -> None:
        decl = _make_declaration(scope_confirmed=True, archetype_confirmed=True)
        assert decl.confirmed_count() == 2
        assert decl.unconfirmed_count() == 2

    def test_fully_confirmed(self) -> None:
        decl = _make_declaration(
            scope_confirmed=True,
            archetype_confirmed=True,
            domain_confirmed=True,
            cap_confirmed=True,
        )
        assert decl.confirmed_count() == 4
        assert decl.unconfirmed_count() == 0

    def test_completion_percentage(self) -> None:
        decl = _make_declaration(scope_confirmed=True, archetype_confirmed=True)
        pct = decl.compute_completion()
        assert pct == 50.0

    def test_full_completion(self) -> None:
        decl = _make_declaration(
            scope_confirmed=True,
            archetype_confirmed=True,
            domain_confirmed=True,
            cap_confirmed=True,
        )
        pct = decl.compute_completion()
        assert pct == 100.0

    def test_serialization_round_trip(self) -> None:
        decl = _make_declaration(scope_confirmed=True)
        data = decl.model_dump(mode="json")
        restored = Declaration.model_validate(data)
        assert restored.id == decl.id
        assert restored.confirmed_count() == 1
