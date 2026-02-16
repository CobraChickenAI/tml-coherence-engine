"""Tests for confirmation persistence — TUI writes confirmation results back to storage."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from tml_engine.confirmation.app import CoherenceApp
from tml_engine.confirmation.mock_data import (
    build_mock_archetype,
    build_mock_capabilities,
    build_mock_declaration,
    build_mock_scope,
)
from tml_engine.confirmation.provenance import make_provenance_entry
from tml_engine.storage.sqlite import StorageEngine


@pytest_asyncio.fixture
async def storage(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = StorageEngine(db_path)
    await engine.initialize()
    yield engine
    await engine.close()


@pytest_asyncio.fixture
async def seeded_storage(storage: StorageEngine):
    """Storage with identity and primitives pre-loaded from mock data."""
    scope = build_mock_scope()
    arch = build_mock_archetype()
    caps = build_mock_capabilities()

    # Create identity
    await storage.upsert_identity(
        identity_id="id-michael",
        email=scope.owner_identity.email,
        display_name=scope.owner_identity.display_name,
    )

    # Store scope
    await storage.store_primitive(
        primitive_id=scope.id,
        primitive_type="scope",
        scope_id=None,
        data=scope.model_dump(mode="json"),
        source=scope.source.source_type,
        identity_id="id-michael",
    )

    # Store archetype
    await storage.store_primitive(
        primitive_id=arch.id,
        primitive_type="archetype",
        scope_id=scope.id,
        data=arch.model_dump(mode="json"),
        source=arch.source.source_type,
        identity_id="id-michael",
    )

    # Store capabilities
    for cap in caps:
        await storage.store_primitive(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=scope.id,
            data=cap.model_dump(mode="json"),
            source=cap.source.source_type,
            identity_id="id-michael",
        )

    return storage


class TestPersistConfirmation:
    @pytest.mark.asyncio
    async def test_persist_confirmation_updates_db(self, seeded_storage: StorageEngine) -> None:
        """Confirmation persistence writes status and provenance to storage."""
        declaration = build_mock_declaration()
        app = CoherenceApp(
            declaration=declaration,
            storage=seeded_storage,
            identity_id="id-michael",
        )

        arch = declaration.archetypes[0]
        actor = declaration.scope.owner_identity
        entry = make_provenance_entry(
            scope_id=arch.scope_id,
            primitive_id=arch.id,
            primitive_type="archetype",
            action="confirmed",
            actor=actor,
            details={"field": "role"},
        )

        await app.persist_confirmation(
            primitive_id=arch.id,
            primitive_type="archetype",
            scope_id=arch.scope_id,
            status="confirmed",
            actor_email=actor.email,
            provenance_entry=entry,
        )

        # Verify primitive confirmation status
        row = await seeded_storage.get_primitive(arch.id)
        assert row is not None
        assert row["confirmation_status"] == "confirmed"
        assert row["confirmed_by"] == actor.email

        # Verify provenance entry
        prov = await seeded_storage.get_provenance(primitive_id=arch.id)
        assert len(prov) == 1
        assert prov[0]["action"] == "confirmed"

    @pytest.mark.asyncio
    async def test_persist_confirmation_noop_without_storage(self) -> None:
        """When storage is None (mock mode), persist does nothing."""
        declaration = build_mock_declaration()
        app = CoherenceApp(declaration=declaration, storage=None)

        arch = declaration.archetypes[0]
        actor = declaration.scope.owner_identity
        entry = make_provenance_entry(
            scope_id=arch.scope_id,
            primitive_id=arch.id,
            primitive_type="archetype",
            action="confirmed",
            actor=actor,
        )

        # Should not raise
        await app.persist_confirmation(
            primitive_id=arch.id,
            primitive_type="archetype",
            scope_id=arch.scope_id,
            status="confirmed",
            actor_email=actor.email,
            provenance_entry=entry,
        )

    @pytest.mark.asyncio
    async def test_persist_corrected_status(self, seeded_storage: StorageEngine) -> None:
        """Corrected confirmations are persisted with status 'corrected'."""
        declaration = build_mock_declaration()
        app = CoherenceApp(
            declaration=declaration,
            storage=seeded_storage,
            identity_id="id-michael",
        )

        cap = declaration.capabilities[0]
        actor = declaration.scope.owner_identity
        entry = make_provenance_entry(
            scope_id=cap.scope_id,
            primitive_id=cap.id,
            primitive_type="capability",
            action="corrected",
            actor=actor,
            details={"field": "description"},
        )

        await app.persist_confirmation(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=cap.scope_id,
            status="corrected",
            actor_email=actor.email,
            provenance_entry=entry,
        )

        row = await seeded_storage.get_primitive(cap.id)
        assert row is not None
        assert row["confirmation_status"] == "corrected"

    @pytest.mark.asyncio
    async def test_persist_flagged_status(self, seeded_storage: StorageEngine) -> None:
        """Flagged confirmations are persisted with status 'flagged'."""
        declaration = build_mock_declaration()
        app = CoherenceApp(
            declaration=declaration,
            storage=seeded_storage,
            identity_id="id-michael",
        )

        cap = declaration.capabilities[1]
        actor = declaration.scope.owner_identity
        entry = make_provenance_entry(
            scope_id=cap.scope_id,
            primitive_id=cap.id,
            primitive_type="capability",
            action="flagged",
            actor=actor,
        )

        await app.persist_confirmation(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=cap.scope_id,
            status="flagged",
            actor_email=actor.email,
            provenance_entry=entry,
        )

        row = await seeded_storage.get_primitive(cap.id)
        assert row is not None
        assert row["confirmation_status"] == "flagged"


class TestPersistPrimitiveUpdate:
    @pytest.mark.asyncio
    async def test_persist_primitive_update(self, seeded_storage: StorageEngine) -> None:
        """Sub-component updates persist the parent's data JSON."""
        import json

        declaration = build_mock_declaration()
        app = CoherenceApp(
            declaration=declaration,
            storage=seeded_storage,
            identity_id="id-michael",
        )

        cap = declaration.capabilities[0]
        updated_data = cap.model_dump(mode="json")

        await app.persist_primitive_update(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=cap.scope_id,
            data=updated_data,
            source=cap.source.source_type,
        )

        row = await seeded_storage.get_primitive(cap.id)
        assert row is not None
        stored_data = json.loads(row["data"])
        assert stored_data["name"] == cap.name

    @pytest.mark.asyncio
    async def test_persist_primitive_update_noop_without_storage(self) -> None:
        """When storage is None, primitive update does nothing."""
        declaration = build_mock_declaration()
        app = CoherenceApp(declaration=declaration, storage=None)

        cap = declaration.capabilities[0]
        # Should not raise
        await app.persist_primitive_update(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=cap.scope_id,
            data=cap.model_dump(mode="json"),
            source=cap.source.source_type,
        )


class TestPersistDeclarationSnapshot:
    @pytest.mark.asyncio
    async def test_persist_declaration_snapshot(self, seeded_storage: StorageEngine) -> None:
        """Declaration snapshot is stored on completion."""
        import json

        declaration = build_mock_declaration()
        app = CoherenceApp(
            declaration=declaration,
            storage=seeded_storage,
            identity_id="id-michael",
        )

        await app.persist_declaration_snapshot()

        row = await seeded_storage.get_declaration(declaration.id)
        assert row is not None
        assert row["version"] == declaration.version
        assert row["scope_id"] == declaration.scope.id
        data = json.loads(row["data"])
        assert data["id"] == declaration.id

    @pytest.mark.asyncio
    async def test_persist_declaration_snapshot_noop_without_storage(self) -> None:
        """When storage is None, declaration snapshot does nothing."""
        declaration = build_mock_declaration()
        app = CoherenceApp(declaration=declaration, storage=None)

        # Should not raise
        await app.persist_declaration_snapshot()


class TestBuildDeclarationReconstructsConfirmation:
    @pytest.mark.asyncio
    async def test_reconstruction_from_db_columns(self, seeded_storage: StorageEngine) -> None:
        """build_declaration_from_storage reconstructs ConfirmationRecord from DB."""
        from tml_engine.pipeline import build_declaration_from_storage

        scope = build_mock_scope()
        arch = build_mock_archetype()

        # Confirm the archetype in storage
        await seeded_storage.update_confirmation(
            arch.id,
            status="confirmed",
            confirmed_by="michael@conversion.com",
        )

        declaration = await build_declaration_from_storage(seeded_storage, scope.id)
        assert declaration is not None
        assert len(declaration.archetypes) >= 1

        loaded_arch = declaration.archetypes[0]
        assert loaded_arch.confirmation is not None
        assert loaded_arch.confirmation.status.value == "confirmed"
        assert loaded_arch.confirmation.confirmed_by.email == "michael@conversion.com"

    @pytest.mark.asyncio
    async def test_unconfirmed_has_no_confirmation(self, seeded_storage: StorageEngine) -> None:
        """Unconfirmed primitives have confirmation=None after loading."""
        from tml_engine.pipeline import build_declaration_from_storage

        scope = build_mock_scope()

        declaration = await build_declaration_from_storage(seeded_storage, scope.id)
        assert declaration is not None

        # All primitives should be unconfirmed (no ConfirmationRecord)
        for cap in declaration.capabilities:
            assert cap.confirmation is None


class TestFullRoundTrip:
    @pytest.mark.asyncio
    async def test_store_confirm_rebuild(self, seeded_storage: StorageEngine) -> None:
        """Full round-trip: store → confirm → rebuild → verify."""
        from tml_engine.pipeline import build_declaration_from_storage

        declaration = build_mock_declaration()
        scope = declaration.scope
        app = CoherenceApp(
            declaration=declaration,
            storage=seeded_storage,
            identity_id="id-michael",
        )

        # Confirm a capability
        cap = declaration.capabilities[0]
        actor = scope.owner_identity
        entry = make_provenance_entry(
            scope_id=cap.scope_id,
            primitive_id=cap.id,
            primitive_type="capability",
            action="confirmed",
            actor=actor,
            details={"field": "description"},
        )
        await app.persist_confirmation(
            primitive_id=cap.id,
            primitive_type="capability",
            scope_id=cap.scope_id,
            status="confirmed",
            actor_email=actor.email,
            provenance_entry=entry,
        )

        # Persist declaration snapshot
        await app.persist_declaration_snapshot()

        # Rebuild from storage
        rebuilt = await build_declaration_from_storage(seeded_storage, scope.id)
        assert rebuilt is not None

        # Find the confirmed capability
        rebuilt_cap = next(c for c in rebuilt.capabilities if c.id == cap.id)
        assert rebuilt_cap.confirmation is not None
        assert rebuilt_cap.confirmation.status.value == "confirmed"

        # Verify provenance entries exist
        prov = await seeded_storage.get_provenance(primitive_id=cap.id)
        assert len(prov) >= 1
        assert any(p["action"] == "confirmed" for p in prov)

        # Verify declaration snapshot exists
        decl_row = await seeded_storage.get_declaration(declaration.id)
        assert decl_row is not None
