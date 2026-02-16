"""Tests for SQLite storage layer."""

import json
from pathlib import Path

import pytest
import pytest_asyncio

from tml_engine.storage.sqlite import StorageEngine


@pytest_asyncio.fixture
async def storage(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = StorageEngine(db_path)
    await engine.initialize()
    yield engine
    await engine.close()


@pytest.mark.asyncio
async def test_initialize_creates_tables(storage: StorageEngine) -> None:
    cursor = await storage.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    rows = await cursor.fetchall()
    table_names = {row[0] for row in rows}
    assert "identities" in table_names
    assert "primitives" in table_names
    assert "provenance" in table_names
    assert "declarations" in table_names
    assert "extractions" in table_names
    assert "interview_sessions" in table_names


@pytest.mark.asyncio
async def test_upsert_and_get_identity(storage: StorageEngine) -> None:
    await storage.upsert_identity(
        identity_id="id-1",
        email="michael@cobrachicken.ai",
        display_name="Michael",
        title="CEO",
    )
    result = await storage.get_identity("id-1")
    assert result is not None
    assert result["email"] == "michael@cobrachicken.ai"
    assert result["title"] == "CEO"


@pytest.mark.asyncio
async def test_upsert_identity_updates(storage: StorageEngine) -> None:
    await storage.upsert_identity(identity_id="id-1", email="a@b.com", display_name="Alice")
    await storage.upsert_identity(identity_id="id-1", email="a@b.com", display_name="Alice Updated")
    result = await storage.get_identity("id-1")
    assert result is not None
    assert result["display_name"] == "Alice Updated"


@pytest.mark.asyncio
async def test_store_and_get_primitive(storage: StorageEngine) -> None:
    data = {"name": "Test Scope", "description": "A test scope"}
    await storage.store_primitive(
        primitive_id="scope-1",
        primitive_type="scope",
        scope_id=None,
        data=data,
        source="interview:session-1",
    )
    result = await storage.get_primitive("scope-1")
    assert result is not None
    assert result["type"] == "scope"
    assert json.loads(result["data"]) == data


@pytest.mark.asyncio
async def test_list_primitives_by_type(storage: StorageEngine) -> None:
    await storage.store_primitive(
        primitive_id="s1", primitive_type="scope", scope_id=None, data={}, source="test"
    )
    await storage.store_primitive(
        primitive_id="d1", primitive_type="domain", scope_id="s1", data={}, source="test"
    )
    await storage.store_primitive(
        primitive_id="d2", primitive_type="domain", scope_id="s1", data={}, source="test"
    )
    domains = await storage.list_primitives(primitive_type="domain")
    assert len(domains) == 2
    scopes = await storage.list_primitives(primitive_type="scope")
    assert len(scopes) == 1


@pytest.mark.asyncio
async def test_update_confirmation(storage: StorageEngine) -> None:
    await storage.store_primitive(
        primitive_id="cap-1", primitive_type="capability", scope_id="s1", data={}, source="test"
    )
    await storage.update_confirmation(
        "cap-1", status="confirmed", confirmed_by="michael@cobrachicken.ai"
    )
    result = await storage.get_primitive("cap-1")
    assert result is not None
    assert result["confirmation_status"] == "confirmed"
    assert result["confirmed_by"] == "michael@cobrachicken.ai"


@pytest.mark.asyncio
async def test_append_and_get_provenance(storage: StorageEngine) -> None:
    await storage.upsert_identity(identity_id="id-1", email="test@test.com", display_name="Test")
    await storage.store_primitive(
        primitive_id="cap-1", primitive_type="capability", scope_id="s1", data={}, source="test"
    )
    await storage.append_provenance(
        provenance_id="prov-1",
        scope_id="s1",
        primitive_id="cap-1",
        primitive_type="capability",
        action="confirmed",
        actor_identity_id="id-1",
        details={"status": "confirmed"},
    )
    entries = await storage.get_provenance(primitive_id="cap-1")
    assert len(entries) == 1
    assert entries[0]["action"] == "confirmed"


@pytest.mark.asyncio
async def test_extraction_lifecycle(storage: StorageEngine) -> None:
    await storage.create_extraction(
        extraction_id="ext-1",
        source_type="web",
        source_identifier="https://example.com",
    )
    await storage.complete_extraction("ext-1")
    cursor = await storage.db.execute("SELECT * FROM extractions WHERE id = ?", ("ext-1",))
    row = await cursor.fetchone()
    assert dict(row)["status"] == "completed"


@pytest.mark.asyncio
async def test_store_and_get_declaration(storage: StorageEngine) -> None:
    await storage.store_declaration(
        declaration_id="decl-1",
        version="0.1.0",
        scope_id="scope-1",
        data={"id": "decl-1", "version": "0.1.0"},
        completion=42.5,
    )
    result = await storage.get_declaration("decl-1")
    assert result is not None
    assert result["version"] == "0.1.0"
    assert result["completion_percentage"] == 42.5


@pytest.mark.asyncio
async def test_interview_session_lifecycle(storage: StorageEngine) -> None:
    await storage.upsert_identity(identity_id="id-1", email="test@test.com", display_name="Test")
    await storage.create_interview_session(
        session_id="sess-1", identity_id="id-1", phase="context_setting"
    )
    await storage.update_interview_session(
        "sess-1",
        phase="archetype_discovery",
        conversation_history=[{"role": "assistant", "content": "Tell me about your role."}],
        status="in_progress",
    )
    result = await storage.get_interview_session("sess-1")
    assert result is not None
    assert result["phase"] == "archetype_discovery"
    history = json.loads(result["conversation_history"])
    assert len(history) == 1


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(storage: StorageEngine) -> None:
    assert await storage.get_identity("nope") is None
    assert await storage.get_primitive("nope") is None
    assert await storage.get_declaration("nope") is None
    assert await storage.get_interview_session("nope") is None


@pytest.mark.asyncio
async def test_get_identity_by_email(storage: StorageEngine) -> None:
    await storage.upsert_identity(
        identity_id="id-1",
        email="alice@example.com",
        display_name="Alice",
    )
    result = await storage.get_identity_by_email("alice@example.com")
    assert result is not None
    assert result["id"] == "id-1"
    assert result["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_get_identity_by_email_not_found(storage: StorageEngine) -> None:
    result = await storage.get_identity_by_email("nobody@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_list_primitives_by_identity(storage: StorageEngine) -> None:
    await storage.store_primitive(
        primitive_id="s1",
        primitive_type="scope",
        scope_id=None,
        data={},
        source="test",
        identity_id="id-1",
    )
    await storage.store_primitive(
        primitive_id="d1",
        primitive_type="domain",
        scope_id="s1",
        data={},
        source="test",
        identity_id="id-1",
    )
    await storage.store_primitive(
        primitive_id="d2",
        primitive_type="domain",
        scope_id="s1",
        data={},
        source="test",
        identity_id="id-2",
    )

    result = await storage.list_primitives_by_identity("id-1")
    assert len(result) == 2
    ids = {r["id"] for r in result}
    assert "s1" in ids
    assert "d1" in ids
    assert "d2" not in ids
