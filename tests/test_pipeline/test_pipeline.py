"""Tests for the pipeline module."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio

from tml_engine.models.identity import ExtractionSource, HumanIdentity
from tml_engine.models.primitives import (
    Archetype,
    Capability,
    DecisionFactor,
    Domain,
    Scope,
    SkillReference,
)
from tml_engine.pipeline import build_declaration_from_storage, find_scope_for_identity
from tml_engine.storage.sqlite import StorageEngine


def _now() -> datetime:
    return datetime.now(UTC)


def _source() -> ExtractionSource:
    return ExtractionSource(source_type="test", source_identifier="test", extracted_at=_now())


def _identity() -> HumanIdentity:
    return HumanIdentity(email="test@example.com", display_name="Test User")


@pytest_asyncio.fixture
async def storage(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = StorageEngine(db_path)
    await engine.initialize()
    yield engine
    await engine.close()


async def _store_scope(
    storage: StorageEngine, scope_id: str = "scope-1", identity_id: str = "id-1"
) -> Scope:
    """Helper to store a scope primitive."""
    scope = Scope(
        id=scope_id,
        name="Test Scope",
        description="A test scope",
        owner_identity=_identity(),
        source=_source(),
    )
    await storage.store_primitive(
        primitive_id=scope_id,
        primitive_type="scope",
        scope_id=None,
        data=scope.model_dump(mode="json"),
        source="test",
        identity_id=identity_id,
    )
    return scope


async def _store_domain(
    storage: StorageEngine, scope_id: str = "scope-1", identity_id: str = "id-1"
) -> Domain:
    domain = Domain(
        id="dom-1",
        scope_id=scope_id,
        name="Test Domain",
        description="A test domain",
        outcome_definition="Success",
        accountable_archetype_id="arch-1",
        source=_source(),
    )
    await storage.store_primitive(
        primitive_id="dom-1",
        primitive_type="domain",
        scope_id=scope_id,
        data=domain.model_dump(mode="json"),
        source="test",
        identity_id=identity_id,
    )
    return domain


async def _store_archetype(
    storage: StorageEngine, scope_id: str = "scope-1", identity_id: str = "id-1"
) -> Archetype:
    arch = Archetype(
        id="arch-1",
        scope_id=scope_id,
        identity=_identity(),
        role_name="Test Role",
        role_description="A test role",
        primary_responsibilities=["Do things"],
        decision_authority=["Decide things"],
        accountability_boundaries=["Not other things"],
        source=_source(),
    )
    await storage.store_primitive(
        primitive_id="arch-1",
        primitive_type="archetype",
        scope_id=scope_id,
        data=arch.model_dump(mode="json"),
        source="test",
        identity_id=identity_id,
    )
    return arch


async def _store_capability(
    storage: StorageEngine, scope_id: str = "scope-1", identity_id: str = "id-1"
) -> Capability:
    cap = Capability(
        id="cap-1",
        scope_id=scope_id,
        domain_id="dom-1",
        name="Test Capability",
        description="A test capability",
        outcome="Good outcome",
        decision_factors=[
            DecisionFactor(name="Factor 1", description="Important", weight="primary")
        ],
        heuristics=["Rule of thumb"],
        anti_patterns=["Bad practice"],
        exceptions=[],
        skills=[SkillReference(id="sk-1", name="Tool", description="A tool", skill_type="tool")],
        source=_source(),
    )
    await storage.store_primitive(
        primitive_id="cap-1",
        primitive_type="capability",
        scope_id=scope_id,
        data=cap.model_dump(mode="json"),
        source="test",
        identity_id=identity_id,
    )
    return cap


@pytest.mark.asyncio
async def test_build_declaration_from_storage(storage: StorageEngine) -> None:
    identity_id = "id-1"
    await storage.upsert_identity(
        identity_id=identity_id, email="test@example.com", display_name="Test"
    )

    await _store_scope(storage, identity_id=identity_id)
    await _store_archetype(storage, identity_id=identity_id)
    await _store_domain(storage, identity_id=identity_id)
    await _store_capability(storage, identity_id=identity_id)

    declaration = await build_declaration_from_storage(storage, "scope-1")

    assert declaration is not None
    assert declaration.scope.id == "scope-1"
    assert len(declaration.archetypes) == 1
    assert len(declaration.domains) == 1
    assert len(declaration.capabilities) == 1
    assert declaration.archetypes[0].role_name == "Test Role"
    assert declaration.capabilities[0].name == "Test Capability"


@pytest.mark.asyncio
async def test_build_declaration_nonexistent_scope(storage: StorageEngine) -> None:
    result = await build_declaration_from_storage(storage, "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_build_declaration_with_provenance(storage: StorageEngine) -> None:
    identity_id = "id-1"
    await storage.upsert_identity(
        identity_id=identity_id, email="test@example.com", display_name="Test"
    )
    await _store_scope(storage, identity_id=identity_id)

    await storage.append_provenance(
        provenance_id="prov-1",
        scope_id="scope-1",
        primitive_id="scope-1",
        primitive_type="scope",
        action="structured",
        actor_identity_id=identity_id,
        details={"action": "structured"},
    )

    declaration = await build_declaration_from_storage(storage, "scope-1")
    assert declaration is not None
    assert len(declaration.provenance) >= 1


@pytest.mark.asyncio
async def test_build_declaration_completion(storage: StorageEngine) -> None:
    identity_id = "id-1"
    await storage.upsert_identity(
        identity_id=identity_id, email="test@example.com", display_name="Test"
    )
    await _store_scope(storage, identity_id=identity_id)
    await _store_domain(storage, identity_id=identity_id)

    declaration = await build_declaration_from_storage(storage, "scope-1")
    assert declaration is not None
    assert declaration.completion_percentage == 0.0  # Nothing confirmed


@pytest.mark.asyncio
async def test_find_scope_for_identity(storage: StorageEngine) -> None:
    identity_id = "id-1"
    await storage.upsert_identity(
        identity_id=identity_id, email="test@example.com", display_name="Test"
    )
    await _store_scope(storage, identity_id=identity_id)

    scope_id = await find_scope_for_identity(storage, "test@example.com")
    assert scope_id == "scope-1"


@pytest.mark.asyncio
async def test_find_scope_for_unknown_identity(storage: StorageEngine) -> None:
    scope_id = await find_scope_for_identity(storage, "unknown@example.com")
    assert scope_id is None


@pytest.mark.asyncio
async def test_find_scope_from_non_scope_primitive(storage: StorageEngine) -> None:
    identity_id = "id-1"
    await storage.upsert_identity(
        identity_id=identity_id, email="test@example.com", display_name="Test"
    )

    # Store only a domain (not a scope) linked to this identity
    await storage.store_primitive(
        primitive_id="dom-only",
        primitive_type="domain",
        scope_id="scope-abc",
        data={},
        source="test",
        identity_id=identity_id,
    )

    scope_id = await find_scope_for_identity(storage, "test@example.com")
    assert scope_id == "scope-abc"
