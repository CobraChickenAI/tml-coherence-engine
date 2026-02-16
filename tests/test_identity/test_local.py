"""Tests for the local identity provider."""

from pathlib import Path

import pytest
import pytest_asyncio

from tml_engine.identity.local import LocalIdentityProvider
from tml_engine.storage.sqlite import StorageEngine


@pytest_asyncio.fixture
async def storage(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = StorageEngine(db_path)
    await engine.initialize()
    yield engine
    await engine.close()


@pytest_asyncio.fixture
async def provider(storage: StorageEngine):
    return LocalIdentityProvider(storage)


@pytest.mark.asyncio
async def test_resolve_existing_identity(
    storage: StorageEngine, provider: LocalIdentityProvider
) -> None:
    await storage.upsert_identity(
        identity_id="id-1",
        email="alice@example.com",
        display_name="Alice Smith",
        title="Engineer",
        department="Platform",
    )
    identity = await provider.resolve("alice@example.com")
    assert identity.email == "alice@example.com"
    assert identity.display_name == "Alice Smith"
    assert identity.title == "Engineer"
    assert identity.department == "Platform"


@pytest.mark.asyncio
async def test_resolve_unknown_creates_minimal(provider: LocalIdentityProvider) -> None:
    identity = await provider.resolve("bob.jones@example.com")
    assert identity.email == "bob.jones@example.com"
    assert identity.display_name == "Bob Jones"
    assert identity.title is None


@pytest.mark.asyncio
async def test_resolve_underscore_email(provider: LocalIdentityProvider) -> None:
    identity = await provider.resolve("jane_doe@example.com")
    assert identity.display_name == "Jane Doe"


@pytest.mark.asyncio
async def test_list_available_empty(provider: LocalIdentityProvider) -> None:
    result = await provider.list_available()
    assert result == []


@pytest.mark.asyncio
async def test_list_available_with_identities(
    storage: StorageEngine, provider: LocalIdentityProvider
) -> None:
    await storage.upsert_identity(
        identity_id="id-1",
        email="alice@example.com",
        display_name="Alice",
    )
    await storage.upsert_identity(
        identity_id="id-2",
        email="bob@example.com",
        display_name="Bob",
    )
    result = await provider.list_available()
    assert len(result) == 2
    emails = {r.email for r in result}
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails
