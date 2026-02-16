"""End-to-end local validation: extract → confirm → export.

This test exercises the full pipeline without external API calls by using
mock data through the actual storage, pipeline, and export code paths.

Validates Stage 6 completion: every confirm/correct/flag action persists to SQLite,
and `build_declaration_from_storage` reconstructs confirmation status from DB columns.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tml_engine.confirmation.mock_data import (
    MOCK_IDENTITY,
    build_mock_archetype,
    build_mock_bindings,
    build_mock_capabilities,
    build_mock_connectors,
    build_mock_domains,
    build_mock_policies,
    build_mock_scope,
    build_mock_views,
)
from tml_engine.confirmation.provenance import make_provenance_entry
from tml_engine.export.json import export_declaration_json
from tml_engine.export.yaml import export_declaration_yaml
from tml_engine.models.identity import ConfirmationStatus
from tml_engine.pipeline import build_declaration_from_storage, find_scope_for_identity
from tml_engine.storage.sqlite import StorageEngine


@pytest.fixture
async def storage(tmp_path: Path) -> StorageEngine:
    """Create and initialize a temporary StorageEngine."""
    db_path = tmp_path / "e2e_test.db"
    engine = StorageEngine(db_path)
    await engine.initialize()
    yield engine
    await engine.close()


async def _seed_mock_data(storage: StorageEngine) -> str:
    """Persist the full mock dataset into storage, simulating extract → structure → persist.

    Returns the scope_id.
    """
    scope = build_mock_scope()
    archetype = build_mock_archetype()
    domains = build_mock_domains()
    capabilities = build_mock_capabilities()
    policies = build_mock_policies()
    connectors = build_mock_connectors()
    bindings = build_mock_bindings()
    views = build_mock_views()

    # Create identity
    identity_id = "id-e2e-001"
    await storage.upsert_identity(
        identity_id=identity_id,
        email=MOCK_IDENTITY.email,
        display_name=MOCK_IDENTITY.display_name,
        title=MOCK_IDENTITY.title,
        department=MOCK_IDENTITY.department,
    )

    # Create extraction record
    extraction_id = "ext-e2e-001"
    await storage.create_extraction(
        extraction_id=extraction_id,
        source_type="web",
        source_identifier="https://conversion.com",
    )

    # Store scope (scope_id=None for root scope, matching pipeline.py behavior)
    await storage.store_primitive(
        primitive_id=scope.id,
        primitive_type="scope",
        scope_id=None,
        data=scope.model_dump(mode="json"),
        source="web:https://conversion.com",
        identity_id=identity_id,
        extraction_id=extraction_id,
    )

    # Store archetype
    await storage.store_primitive(
        primitive_id=archetype.id,
        primitive_type="archetype",
        scope_id=scope.id,
        data=archetype.model_dump(mode="json"),
        source="web:https://conversion.com",
        identity_id=identity_id,
        extraction_id=extraction_id,
    )

    # Store domains
    for domain in domains:
        await storage.store_primitive(
            primitive_id=domain.id,
            primitive_type="domain",
            scope_id=scope.id,
            data=domain.model_dump(mode="json"),
            source="web:https://conversion.com",
            identity_id=identity_id,
            extraction_id=extraction_id,
        )

    # Store capabilities
    for cap in capabilities:
        await storage.store_primitive(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=scope.id,
            data=cap.model_dump(mode="json"),
            source="web:https://conversion.com",
            identity_id=identity_id,
            extraction_id=extraction_id,
        )

    # Store policies
    for pol in policies:
        await storage.store_primitive(
            primitive_id=pol.id,
            primitive_type="policy",
            scope_id=scope.id,
            data=pol.model_dump(mode="json"),
            source="web:https://conversion.com",
            identity_id=identity_id,
            extraction_id=extraction_id,
        )

    # Store connectors
    for conn in connectors:
        await storage.store_primitive(
            primitive_id=conn.id,
            primitive_type="connector",
            scope_id=scope.id,
            data=conn.model_dump(mode="json"),
            source="web:https://conversion.com",
            identity_id=identity_id,
            extraction_id=extraction_id,
        )

    # Store bindings
    for bind in bindings:
        await storage.store_primitive(
            primitive_id=bind.id,
            primitive_type="binding",
            scope_id=scope.id,
            data=bind.model_dump(mode="json"),
            source="web:https://conversion.com",
            identity_id=identity_id,
            extraction_id=extraction_id,
        )

    # Store views
    for view in views:
        await storage.store_primitive(
            primitive_id=view.id,
            primitive_type="view",
            scope_id=scope.id,
            data=view.model_dump(mode="json"),
            source="web:https://conversion.com",
            identity_id=identity_id,
            extraction_id=extraction_id,
        )

    # Emit provenance for structuring
    await storage.append_provenance(
        provenance_id="prov-e2e-struct-001",
        scope_id=scope.id,
        primitive_id=scope.id,
        primitive_type="scope",
        action="structured",
        actor_identity_id=identity_id,
        details={"action": "structured", "timestamp": datetime.now(UTC).isoformat()},
    )

    await storage.complete_extraction(extraction_id)
    return scope.id


@pytest.mark.asyncio
async def test_e2e_init_and_seed(storage: StorageEngine) -> None:
    """Phase 1: Verify storage initialization and data seeding."""
    scope_id = await _seed_mock_data(storage)

    # Verify all primitives stored
    primitives = await storage.list_primitives(scope_id=scope_id)
    # Scope is stored with scope_id=None, so it won't appear in this query
    assert len(primitives) >= 12  # 1 arch + 3 dom + 3 cap + 3 pol + 2 conn + 2 bind + 1 view = 15

    # Verify scope exists
    scope_row = await storage.get_primitive("scope-ops-001")
    assert scope_row is not None
    assert scope_row["type"] == "scope"

    # Verify identity exists
    identity = await storage.get_identity_by_email("michael@conversion.com")
    assert identity is not None
    assert identity["display_name"] == "Michael Chen"

    # Verify extraction completed
    primitives_by_type = {}
    for p in primitives:
        ptype = p["type"]
        primitives_by_type[ptype] = primitives_by_type.get(ptype, 0) + 1

    assert primitives_by_type.get("archetype", 0) == 1
    assert primitives_by_type.get("domain", 0) == 3
    assert primitives_by_type.get("capability", 0) == 3
    assert primitives_by_type.get("policy", 0) == 3
    assert primitives_by_type.get("connector", 0) == 2
    assert primitives_by_type.get("binding", 0) == 2

    # All primitives should be unconfirmed
    for p in primitives:
        assert p["confirmation_status"] == "unconfirmed"


@pytest.mark.asyncio
async def test_e2e_build_declaration_from_storage(storage: StorageEngine) -> None:
    """Phase 2: Build a Declaration from stored primitives."""
    scope_id = await _seed_mock_data(storage)

    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None

    # Verify all primitive types are loaded
    assert len(declaration.archetypes) == 1
    assert len(declaration.domains) == 3
    assert len(declaration.capabilities) == 3
    assert len(declaration.policies) == 3
    assert len(declaration.connectors) == 2
    assert len(declaration.bindings) == 2

    # Verify scope
    assert declaration.scope.id == scope_id
    assert declaration.scope.name == "Conversion Operations"
    assert declaration.scope.owner_identity.email == "michael@conversion.com"

    # Verify archetype details survived serialization roundtrip
    arch = declaration.archetypes[0]
    assert arch.role_name == "VP of Operations"
    assert len(arch.primary_responsibilities) == 5
    assert len(arch.decision_authority) == 4

    # Verify capability sub-components
    carrier_cap = next(c for c in declaration.capabilities if c.id == "cap-carrier-safety")
    assert len(carrier_cap.decision_factors) == 4
    assert len(carrier_cap.heuristics) == 3
    assert len(carrier_cap.skills) == 2
    assert len(carrier_cap.exceptions) == 1

    # All primitives should be unconfirmed at this point
    assert declaration.confirmed_count() == 0
    assert declaration.compute_completion() == 0.0


@pytest.mark.asyncio
async def test_e2e_find_scope_for_identity(storage: StorageEngine) -> None:
    """Verify find_scope_for_identity resolves correctly."""
    scope_id = await _seed_mock_data(storage)

    found = await find_scope_for_identity(storage, "michael@conversion.com")
    assert found == scope_id

    # Non-existent identity returns None
    not_found = await find_scope_for_identity(storage, "nobody@nowhere.com")
    assert not_found is None


@pytest.mark.asyncio
async def test_e2e_confirmation_persistence(storage: StorageEngine) -> None:
    """Phase 3: Simulate confirmation actions and verify persistence.

    This replicates what the TUI screens do: update_confirmation + append_provenance.
    """
    scope_id = await _seed_mock_data(storage)
    identity_row = await storage.get_identity_by_email("michael@conversion.com")
    identity_id = identity_row["id"]

    # --- Confirm the archetype ---
    entry = make_provenance_entry(
        scope_id=scope_id,
        primitive_id="arch-001",
        primitive_type="archetype",
        action="confirmed",
        actor=MOCK_IDENTITY,
        details={"field": "role_name", "assertion_text": "You are VP of Operations"},
    )
    await storage.update_confirmation(
        "arch-001",
        status="confirmed",
        confirmed_by=MOCK_IDENTITY.email,
    )
    await storage.append_provenance(
        provenance_id=entry.id,
        scope_id=scope_id,
        primitive_id="arch-001",
        primitive_type="archetype",
        action="confirmed",
        actor_identity_id=identity_id,
        details=entry.details,
    )

    # --- Correct a domain ---
    entry2 = make_provenance_entry(
        scope_id=scope_id,
        primitive_id="dom-carrier-eval",
        primitive_type="domain",
        action="corrected",
        actor=MOCK_IDENTITY,
        details={"field": "name", "assertion_text": "Carrier Evaluation"},
    )
    await storage.update_confirmation(
        "dom-carrier-eval",
        status="corrected",
        confirmed_by=MOCK_IDENTITY.email,
        original_data={"name": "Carrier Evaluation"},
    )
    await storage.append_provenance(
        provenance_id=entry2.id,
        scope_id=scope_id,
        primitive_id="dom-carrier-eval",
        primitive_type="domain",
        action="corrected",
        actor_identity_id=identity_id,
        details=entry2.details,
    )

    # --- Flag a policy ---
    entry3 = make_provenance_entry(
        scope_id=scope_id,
        primitive_id="pol-margin-target",
        primitive_type="policy",
        action="flagged",
        actor=MOCK_IDENTITY,
        details={"field": "rule", "assertion_text": "Target 12% gross margin"},
    )
    await storage.update_confirmation(
        "pol-margin-target",
        status="flagged",
        confirmed_by=MOCK_IDENTITY.email,
    )
    await storage.append_provenance(
        provenance_id=entry3.id,
        scope_id=scope_id,
        primitive_id="pol-margin-target",
        primitive_type="policy",
        action="flagged",
        actor_identity_id=identity_id,
        details=entry3.details,
    )

    # --- Confirm a capability ---
    entry4 = make_provenance_entry(
        scope_id=scope_id,
        primitive_id="cap-carrier-safety",
        primitive_type="capability",
        action="confirmed",
        actor=MOCK_IDENTITY,
    )
    await storage.update_confirmation(
        "cap-carrier-safety",
        status="confirmed",
        confirmed_by=MOCK_IDENTITY.email,
    )
    await storage.append_provenance(
        provenance_id=entry4.id,
        scope_id=scope_id,
        primitive_id="cap-carrier-safety",
        primitive_type="capability",
        action="confirmed",
        actor_identity_id=identity_id,
        details=entry4.details,
    )

    # --- Confirm a connector ---
    entry5 = make_provenance_entry(
        scope_id=scope_id,
        primitive_id="conn-sales-loads",
        primitive_type="connector",
        action="confirmed",
        actor=MOCK_IDENTITY,
    )
    await storage.update_confirmation(
        "conn-sales-loads",
        status="confirmed",
        confirmed_by=MOCK_IDENTITY.email,
    )
    await storage.append_provenance(
        provenance_id=entry5.id,
        scope_id=scope_id,
        primitive_id="conn-sales-loads",
        primitive_type="connector",
        action="confirmed",
        actor_identity_id=identity_id,
        details=entry5.details,
    )

    # Verify raw DB state
    arch_row = await storage.get_primitive("arch-001")
    assert arch_row["confirmation_status"] == "confirmed"
    assert arch_row["confirmed_by"] == "michael@conversion.com"
    assert arch_row["confirmed_at"] is not None

    dom_row = await storage.get_primitive("dom-carrier-eval")
    assert dom_row["confirmation_status"] == "corrected"
    assert dom_row["original_data"] is not None

    pol_row = await storage.get_primitive("pol-margin-target")
    assert pol_row["confirmation_status"] == "flagged"

    cap_row = await storage.get_primitive("cap-carrier-safety")
    assert cap_row["confirmation_status"] == "confirmed"

    conn_row = await storage.get_primitive("conn-sales-loads")
    assert conn_row["confirmation_status"] == "confirmed"

    # Verify provenance entries were recorded
    prov_rows = await storage.get_provenance(scope_id=scope_id)
    # At least 1 structuring + 5 confirmation provenance entries
    assert len(prov_rows) >= 6


@pytest.mark.asyncio
async def test_e2e_rebuild_declaration_with_confirmations(storage: StorageEngine) -> None:
    """Phase 4: Rebuild Declaration from storage and verify confirmation statuses survive."""
    scope_id = await _seed_mock_data(storage)
    identity_row = await storage.get_identity_by_email("michael@conversion.com")
    identity_id = identity_row["id"]

    # Confirm some primitives
    for pid, ptype, status in [
        ("arch-001", "archetype", "confirmed"),
        ("dom-carrier-eval", "domain", "confirmed"),
        ("dom-load-matching", "domain", "corrected"),
        ("cap-carrier-safety", "capability", "confirmed"),
        ("cap-load-optimization", "capability", "confirmed"),
        ("pol-safety-floor", "policy", "confirmed"),
        ("conn-sales-loads", "connector", "confirmed"),
        ("bind-dispatch", "binding", "confirmed"),
    ]:
        await storage.update_confirmation(pid, status=status, confirmed_by=MOCK_IDENTITY.email)
        entry = make_provenance_entry(
            scope_id=scope_id,
            primitive_id=pid,
            primitive_type=ptype,
            action=status,
            actor=MOCK_IDENTITY,
        )
        await storage.append_provenance(
            provenance_id=entry.id,
            scope_id=scope_id,
            primitive_id=pid,
            primitive_type=ptype,
            action=status,
            actor_identity_id=identity_id,
            details=entry.details,
        )

    # Rebuild declaration
    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None

    # Verify confirmation statuses were reconstructed
    arch = declaration.archetypes[0]
    assert arch.confirmation is not None
    assert arch.confirmation.status == ConfirmationStatus.CONFIRMED
    assert arch.confirmation.confirmed_by.email == "michael@conversion.com"

    # Check domains
    dom_eval = next(d for d in declaration.domains if d.id == "dom-carrier-eval")
    assert dom_eval.confirmation is not None
    assert dom_eval.confirmation.status == ConfirmationStatus.CONFIRMED

    dom_match = next(d for d in declaration.domains if d.id == "dom-load-matching")
    assert dom_match.confirmation is not None
    assert dom_match.confirmation.status == ConfirmationStatus.CORRECTED

    dom_risk = next(d for d in declaration.domains if d.id == "dom-risk-mgmt")
    assert dom_risk.confirmation is None  # Not confirmed yet

    # Check capabilities
    cap_safety = next(c for c in declaration.capabilities if c.id == "cap-carrier-safety")
    assert cap_safety.confirmation is not None
    assert cap_safety.confirmation.status == ConfirmationStatus.CONFIRMED

    cap_risk = next(c for c in declaration.capabilities if c.id == "cap-risk-assessment")
    assert cap_risk.confirmation is None  # Not confirmed

    # Check policy
    pol_floor = next(p for p in declaration.policies if p.id == "pol-safety-floor")
    assert pol_floor.confirmation is not None

    # Check connector
    conn = next(c for c in declaration.connectors if c.id == "conn-sales-loads")
    assert conn.confirmation is not None

    # Check binding
    bind = next(b for b in declaration.bindings if b.id == "bind-dispatch")
    assert bind.confirmation is not None

    # Verify completion percentage
    declaration.compute_completion()
    # 8 confirmed out of total confirmable (scope + 1 arch + 3 dom + 3 cap + 3 pol + 2 conn + 2 bind = 15)
    # scope is not confirmed, so 8 confirmed out of 15
    assert declaration.confirmed_count() == 8
    assert declaration.completion_percentage > 0.0
    assert declaration.completion_percentage == pytest.approx(8 / 15 * 100, abs=0.1)

    # Verify provenance entries are present
    assert len(declaration.provenance) > 0


@pytest.mark.asyncio
async def test_e2e_export_json_with_confirmations(storage: StorageEngine, tmp_path: Path) -> None:
    """Phase 5: Export Declaration as JSON and verify confirmation data is included."""
    scope_id = await _seed_mock_data(storage)
    identity_row = await storage.get_identity_by_email("michael@conversion.com")
    identity_id = identity_row["id"]

    # Confirm a few primitives
    for pid, ptype in [
        ("arch-001", "archetype"),
        ("dom-carrier-eval", "domain"),
        ("cap-carrier-safety", "capability"),
    ]:
        await storage.update_confirmation(pid, status="confirmed", confirmed_by=MOCK_IDENTITY.email)
        entry = make_provenance_entry(
            scope_id=scope_id,
            primitive_id=pid,
            primitive_type=ptype,
            action="confirmed",
            actor=MOCK_IDENTITY,
        )
        await storage.append_provenance(
            provenance_id=entry.id,
            scope_id=scope_id,
            primitive_id=pid,
            primitive_type=ptype,
            action="confirmed",
            actor_identity_id=identity_id,
            details=entry.details,
        )

    # Build and export
    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None

    output_path = tmp_path / "declaration.json"
    export_declaration_json(declaration, output_path)

    # Read back and verify
    exported = json.loads(output_path.read_text())

    # Top-level structure
    assert "scope" in exported
    assert "archetypes" in exported
    assert "domains" in exported
    assert "capabilities" in exported
    assert "provenance" in exported
    assert exported["scope"]["id"] == scope_id

    # Archetype confirmation present in JSON
    arch_data = exported["archetypes"][0]
    assert arch_data["confirmation"] is not None
    assert arch_data["confirmation"]["status"] == "confirmed"
    assert arch_data["confirmation"]["confirmed_by"]["email"] == "michael@conversion.com"

    # Domain confirmation present
    dom_eval_data = next(d for d in exported["domains"] if d["id"] == "dom-carrier-eval")
    assert dom_eval_data["confirmation"] is not None
    assert dom_eval_data["confirmation"]["status"] == "confirmed"

    # Unconfirmed domain has null confirmation
    dom_risk_data = next(d for d in exported["domains"] if d["id"] == "dom-risk-mgmt")
    assert dom_risk_data["confirmation"] is None

    # Capability confirmation present
    cap_data = next(c for c in exported["capabilities"] if c["id"] == "cap-carrier-safety")
    assert cap_data["confirmation"] is not None

    # Capability sub-components survived roundtrip
    assert len(cap_data["decision_factors"]) == 4
    assert len(cap_data["skills"]) == 2
    assert len(cap_data["exceptions"]) == 1

    # Provenance entries present
    assert len(exported["provenance"]) > 0

    # Completion percentage
    assert exported["completion_percentage"] > 0.0


@pytest.mark.asyncio
async def test_e2e_export_yaml_with_confirmations(storage: StorageEngine, tmp_path: Path) -> None:
    """Phase 5b: Export Declaration as YAML and verify it's valid."""
    import yaml

    scope_id = await _seed_mock_data(storage)
    identity_row = await storage.get_identity_by_email("michael@conversion.com")
    identity_id = identity_row["id"]

    # Confirm one primitive
    await storage.update_confirmation(
        "arch-001", status="confirmed", confirmed_by=MOCK_IDENTITY.email
    )
    entry = make_provenance_entry(
        scope_id=scope_id,
        primitive_id="arch-001",
        primitive_type="archetype",
        action="confirmed",
        actor=MOCK_IDENTITY,
    )
    await storage.append_provenance(
        provenance_id=entry.id,
        scope_id=scope_id,
        primitive_id="arch-001",
        primitive_type="archetype",
        action="confirmed",
        actor_identity_id=identity_id,
        details=entry.details,
    )

    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None

    output_path = tmp_path / "declaration.yaml"
    export_declaration_yaml(declaration, output_path)

    # Read back and verify it's valid YAML
    exported = yaml.safe_load(output_path.read_text())
    assert exported["scope"]["id"] == scope_id
    assert exported["archetypes"][0]["confirmation"]["status"] == "confirmed"


@pytest.mark.asyncio
async def test_e2e_status_command_data(storage: StorageEngine) -> None:
    """Phase 6: Verify the data the status command would display."""
    await _seed_mock_data(storage)

    # Before any confirmations
    primitives = await storage.list_primitives()
    type_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for p in primitives:
        ptype = p["type"]
        pstatus = p["confirmation_status"]
        type_counts[ptype] = type_counts.get(ptype, 0) + 1
        status_counts[pstatus] = status_counts.get(pstatus, 0) + 1

    # All should be unconfirmed
    assert status_counts.get("unconfirmed", 0) > 0
    assert status_counts.get("confirmed", 0) == 0

    # After some confirmations
    await storage.update_confirmation(
        "arch-001", status="confirmed", confirmed_by=MOCK_IDENTITY.email
    )
    await storage.update_confirmation(
        "dom-carrier-eval", status="confirmed", confirmed_by=MOCK_IDENTITY.email
    )

    primitives = await storage.list_primitives()
    status_counts = {}
    for p in primitives:
        pstatus = p["confirmation_status"]
        status_counts[pstatus] = status_counts.get(pstatus, 0) + 1

    assert status_counts.get("confirmed", 0) == 2
    assert status_counts.get("unconfirmed", 0) > 0


@pytest.mark.asyncio
async def test_e2e_declaration_snapshot_persistence(storage: StorageEngine) -> None:
    """Phase 7: Verify Declaration snapshot can be stored and retrieved."""
    scope_id = await _seed_mock_data(storage)

    # Build declaration
    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None

    # Confirm some primitives
    await storage.update_confirmation(
        "arch-001", status="confirmed", confirmed_by=MOCK_IDENTITY.email
    )

    # Rebuild with confirmations
    declaration = await build_declaration_from_storage(storage, scope_id)
    declaration.compute_completion()

    # Store declaration snapshot (as the TUI summary screen would)
    await storage.store_declaration(
        declaration_id=declaration.id,
        version=declaration.version,
        scope_id=scope_id,
        data=declaration.model_dump(mode="json"),
        completion=declaration.completion_percentage,
    )

    # Verify stored
    declarations = await storage.list_declarations(scope_id=scope_id)
    assert len(declarations) == 1
    assert declarations[0]["version"] == "0.1.0"
    assert declarations[0]["completion_percentage"] > 0.0

    # Verify data roundtrips
    from tml_engine.models.declaration import Declaration

    stored_data = (
        json.loads(declarations[0]["data"])
        if isinstance(declarations[0]["data"], str)
        else declarations[0]["data"]
    )
    restored = Declaration.model_validate(stored_data)
    assert restored.scope.id == scope_id
    assert restored.archetypes[0].confirmation is not None
    assert restored.archetypes[0].confirmation.status == ConfirmationStatus.CONFIRMED


@pytest.mark.asyncio
async def test_e2e_primitive_update_persistence(storage: StorageEngine) -> None:
    """Phase 8: Verify primitive data updates persist (simulating skill/exception edits)."""
    scope_id = await _seed_mock_data(storage)

    # Load the capability
    cap_row = await storage.get_primitive("cap-carrier-safety")
    cap_data = json.loads(cap_row["data"]) if isinstance(cap_row["data"], str) else cap_row["data"]

    from tml_engine.models.primitives import Capability

    cap = Capability.model_validate(cap_data)

    # Simulate editing a skill name (as the Skills screen would)
    cap.skills[0].name = "Updated FMCSA Lookup Tool"

    # Persist the update
    await storage.store_primitive(
        primitive_id=cap.id,
        primitive_type="capability",
        scope_id=scope_id,
        data=cap.model_dump(mode="json"),
        source="web:https://conversion.com",
    )

    # Rebuild declaration and verify the edit survived
    declaration = await build_declaration_from_storage(storage, scope_id)
    updated_cap = next(c for c in declaration.capabilities if c.id == "cap-carrier-safety")
    assert updated_cap.skills[0].name == "Updated FMCSA Lookup Tool"


@pytest.mark.asyncio
async def test_e2e_full_flow_integration(storage: StorageEngine, tmp_path: Path) -> None:
    """The master integration test: init → seed → confirm → export → verify.

    This is the single test that validates the complete Stage 6 e2e loop.
    """
    # Step 1: Seed (simulates extract)
    scope_id = await _seed_mock_data(storage)

    # Step 2: Verify scope resolution
    found_scope = await find_scope_for_identity(storage, "michael@conversion.com")
    assert found_scope == scope_id

    # Step 3: Build initial declaration (simulates what confirm command does before TUI)
    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None
    assert declaration.confirmed_count() == 0

    # Step 4: Simulate TUI confirmations across all primitive types
    identity_row = await storage.get_identity_by_email("michael@conversion.com")
    identity_id = identity_row["id"]

    confirmations = [
        ("arch-001", "archetype", "confirmed"),
        ("dom-carrier-eval", "domain", "confirmed"),
        ("dom-load-matching", "domain", "confirmed"),
        ("dom-risk-mgmt", "domain", "corrected"),
        ("cap-carrier-safety", "capability", "confirmed"),
        ("cap-load-optimization", "capability", "confirmed"),
        ("cap-risk-assessment", "capability", "flagged"),
        ("pol-safety-floor", "policy", "confirmed"),
        ("pol-insurance-minimum", "policy", "confirmed"),
        ("pol-margin-target", "policy", "confirmed"),
        ("conn-sales-loads", "connector", "confirmed"),
        ("conn-fmcsa-data", "connector", "confirmed"),
        ("bind-dispatch", "binding", "confirmed"),
        ("bind-client-update", "binding", "confirmed"),
    ]

    for pid, ptype, status in confirmations:
        await storage.update_confirmation(pid, status=status, confirmed_by=MOCK_IDENTITY.email)
        entry = make_provenance_entry(
            scope_id=scope_id,
            primitive_id=pid,
            primitive_type=ptype,
            action=status,
            actor=MOCK_IDENTITY,
        )
        await storage.append_provenance(
            provenance_id=entry.id,
            scope_id=scope_id,
            primitive_id=pid,
            primitive_type=ptype,
            action=status,
            actor_identity_id=identity_id,
            details=entry.details,
        )

    # Step 5: Rebuild declaration from storage
    declaration = await build_declaration_from_storage(storage, scope_id)
    assert declaration is not None

    # Step 6: Verify all confirmation statuses reconstructed correctly
    for pid, ptype, expected_status in confirmations:
        if ptype == "archetype":
            prim = next(a for a in declaration.archetypes if a.id == pid)
        elif ptype == "domain":
            prim = next(d for d in declaration.domains if d.id == pid)
        elif ptype == "capability":
            prim = next(c for c in declaration.capabilities if c.id == pid)
        elif ptype == "policy":
            prim = next(p for p in declaration.policies if p.id == pid)
        elif ptype == "connector":
            prim = next(c for c in declaration.connectors if c.id == pid)
        elif ptype == "binding":
            prim = next(b for b in declaration.bindings if b.id == pid)

        assert prim.confirmation is not None, f"{ptype} {pid} should be confirmed"
        assert prim.confirmation.status == ConfirmationStatus(expected_status), (
            f"{ptype} {pid}: expected {expected_status}, got {prim.confirmation.status}"
        )

    # Step 7: Verify completion percentage
    declaration.compute_completion()
    # 12 confirmed + 1 corrected = 13 (flagged does NOT count as confirmed)
    # Unconfirmed: scope + flagged cap-risk-assessment = 2
    assert declaration.confirmed_count() == 13
    assert declaration.completion_percentage == pytest.approx(13 / 15 * 100, abs=0.1)

    # Step 8: Export as JSON
    json_path = tmp_path / "final_declaration.json"
    export_declaration_json(declaration, json_path)

    exported = json.loads(json_path.read_text())

    # Verify exported JSON has confirmation data (13/15 = 86.7%)
    assert exported["completion_percentage"] > 80.0
    assert all(a["confirmation"] is not None for a in exported["archetypes"]), (
        "All archetypes should be confirmed in export"
    )

    # Verify the flagged capability appears correctly
    flagged_cap = next(c for c in exported["capabilities"] if c["id"] == "cap-risk-assessment")
    assert flagged_cap["confirmation"]["status"] == "flagged"

    # Verify corrected domain appears correctly
    corrected_dom = next(d for d in exported["domains"] if d["id"] == "dom-risk-mgmt")
    assert corrected_dom["confirmation"]["status"] == "corrected"

    # Verify provenance trail
    assert len(exported["provenance"]) >= 15  # 1 structuring + 14 confirmations

    # Step 9: Export as YAML
    import yaml

    yaml_path = tmp_path / "final_declaration.yaml"
    export_declaration_yaml(declaration, yaml_path)

    yaml_data = yaml.safe_load(yaml_path.read_text())
    assert yaml_data["completion_percentage"] > 80.0

    # Step 10: Store declaration snapshot
    await storage.store_declaration(
        declaration_id=declaration.id,
        version=declaration.version,
        scope_id=scope_id,
        data=declaration.model_dump(mode="json"),
        completion=declaration.completion_percentage,
    )

    # Verify snapshot stored
    decl_list = await storage.list_declarations(scope_id=scope_id)
    assert len(decl_list) == 1
    assert decl_list[0]["completion_percentage"] > 80.0
