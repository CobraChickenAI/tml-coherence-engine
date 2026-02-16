"""Pipeline — wires extraction, structuring, persistence, and Declaration assembly.

This module connects the independent components (extractors, structurer, storage)
into the end-to-end flow: extract → structure → persist → build Declaration.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from tml_engine.extractors.base import RawExtractionResult
from tml_engine.models.declaration import Declaration
from tml_engine.models.identity import ExtractionSource, HumanIdentity
from tml_engine.models.primitives import (
    Archetype,
    Binding,
    Capability,
    Connector,
    Domain,
    Policy,
    ProvenanceEntry,
    Scope,
    View,
)
from tml_engine.storage.sqlite import StorageEngine
from tml_engine.structurer.llm import LLMStructurer, StructuredPrimitives


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# Mapping from primitive type string to Pydantic model class
_PRIMITIVE_TYPE_MAP: dict[str, type] = {
    "scope": Scope,
    "domain": Domain,
    "capability": Capability,
    "view": View,
    "archetype": Archetype,
    "policy": Policy,
    "connector": Connector,
    "binding": Binding,
    "provenance": ProvenanceEntry,
}


async def persist_structured_primitives(
    storage: StorageEngine,
    structured: StructuredPrimitives,
    scope: Scope,
    extraction_id: str,
    identity_id: str,
    source_label: str,
) -> None:
    """Persist all structured primitives and provenance entries to storage."""
    # Store the scope
    await storage.store_primitive(
        primitive_id=scope.id,
        primitive_type="scope",
        scope_id=None,
        data=scope.model_dump(mode="json"),
        source=source_label,
        identity_id=identity_id,
        extraction_id=extraction_id,
    )
    await _emit_provenance(storage, scope.id, "scope", scope.id, identity_id, "structured")

    # Store each primitive type
    for archetype in structured.archetypes:
        await _store_and_track(
            storage,
            archetype.id,
            "archetype",
            structured.scope_id,
            archetype.model_dump(mode="json"),
            source_label,
            identity_id,
            extraction_id,
        )

    for domain in structured.domains:
        await _store_and_track(
            storage,
            domain.id,
            "domain",
            structured.scope_id,
            domain.model_dump(mode="json"),
            source_label,
            identity_id,
            extraction_id,
        )

    for capability in structured.capabilities:
        await _store_and_track(
            storage,
            capability.id,
            "capability",
            structured.scope_id,
            capability.model_dump(mode="json"),
            source_label,
            identity_id,
            extraction_id,
        )

    for policy in structured.policies:
        await _store_and_track(
            storage,
            policy.id,
            "policy",
            structured.scope_id,
            policy.model_dump(mode="json"),
            source_label,
            identity_id,
            extraction_id,
        )

    for connector in structured.connectors:
        await _store_and_track(
            storage,
            connector.id,
            "connector",
            structured.scope_id,
            connector.model_dump(mode="json"),
            source_label,
            identity_id,
            extraction_id,
        )

    for binding in structured.bindings:
        await _store_and_track(
            storage,
            binding.id,
            "binding",
            structured.scope_id,
            binding.model_dump(mode="json"),
            source_label,
            identity_id,
            extraction_id,
        )


async def _store_and_track(
    storage: StorageEngine,
    primitive_id: str,
    primitive_type: str,
    scope_id: str,
    data: dict,
    source: str,
    identity_id: str,
    extraction_id: str,
) -> None:
    await storage.store_primitive(
        primitive_id=primitive_id,
        primitive_type=primitive_type,
        scope_id=scope_id,
        data=data,
        source=source,
        identity_id=identity_id,
        extraction_id=extraction_id,
    )
    await _emit_provenance(
        storage, primitive_id, primitive_type, scope_id, identity_id, "structured"
    )


async def _emit_provenance(
    storage: StorageEngine,
    primitive_id: str,
    primitive_type: str,
    scope_id: str,
    actor_identity_id: str,
    action: str,
) -> None:
    await storage.append_provenance(
        provenance_id=_gen_id("prov"),
        scope_id=scope_id,
        primitive_id=primitive_id,
        primitive_type=primitive_type,
        action=action,
        actor_identity_id=actor_identity_id,
        details={"action": action, "timestamp": datetime.now(UTC).isoformat()},
    )


async def run_web_extraction(
    url: str,
    identity: HumanIdentity,
    storage: StorageEngine,
    structurer: LLMStructurer,
    *,
    template: str = "default",
) -> str:
    """Run the full web extraction pipeline: extract → structure → persist.

    Returns the scope_id for the created primitives.
    """
    from tml_engine.extractors.web import WebExtractor

    # Ensure identity exists in storage
    identity_id = _gen_id("id")
    await storage.upsert_identity(
        identity_id=identity_id,
        email=identity.email,
        display_name=identity.display_name,
        title=identity.title,
        department=identity.department,
        workspace_id=identity.workspace_id,
    )
    # Re-resolve to get the actual ID (may have been upserted with existing)
    row = await storage.get_identity_by_email(identity.email)
    if row:
        identity_id = row["id"]

    # Create extraction record
    extraction_id = _gen_id("ext")
    await storage.create_extraction(
        extraction_id=extraction_id,
        source_type="web",
        source_identifier=url,
    )

    # Extract
    extractor = WebExtractor()
    config: dict = {"base_url": url}
    if template != "default":
        config["template_path"] = template
    result = await extractor.extract(config)

    # Structure
    scope_id = _gen_id("scope")
    structured = await structurer.structure(result, scope_id, owner_identity=identity)

    # Build scope
    source = ExtractionSource(
        source_type="web",
        source_identifier=url,
        extracted_at=result.extracted_at,
    )
    scope = Scope(
        id=scope_id,
        name=f"Extraction from {url}",
        description=f"Scope created from web extraction of {url}",
        owner_identity=identity,
        source=source,
    )

    # Persist
    await persist_structured_primitives(
        storage,
        structured,
        scope,
        extraction_id,
        identity_id,
        f"web:{url}",
    )
    await storage.complete_extraction(extraction_id)

    return scope_id


async def run_interview_structuring(
    result: RawExtractionResult,
    identity: HumanIdentity,
    storage: StorageEngine,
    structurer: LLMStructurer,
) -> str:
    """Structure and persist a completed interview extraction result.

    Returns the scope_id for the created primitives.
    """
    # Ensure identity exists
    identity_id = _gen_id("id")
    await storage.upsert_identity(
        identity_id=identity_id,
        email=identity.email,
        display_name=identity.display_name,
        title=identity.title,
        department=identity.department,
        workspace_id=identity.workspace_id,
    )
    row = await storage.get_identity_by_email(identity.email)
    if row:
        identity_id = row["id"]

    # Create extraction record
    extraction_id = _gen_id("ext")
    await storage.create_extraction(
        extraction_id=extraction_id,
        source_type="interview",
        source_identifier=identity.email,
    )

    # Structure
    scope_id = _gen_id("scope")
    structured = await structurer.structure(result, scope_id, owner_identity=identity)

    # Build scope
    source = ExtractionSource(
        source_type="interview",
        source_identifier=identity.email,
        extracted_at=result.extracted_at,
    )
    scope = Scope(
        id=scope_id,
        name=f"Interview with {identity.display_name}",
        description=f"Scope created from adaptive interview with {identity.email}",
        owner_identity=identity,
        source=source,
    )

    # Persist
    await persist_structured_primitives(
        storage,
        structured,
        scope,
        extraction_id,
        identity_id,
        f"interview:{identity.email}",
    )
    await storage.complete_extraction(extraction_id)

    return scope_id


async def build_declaration_from_storage(
    storage: StorageEngine,
    scope_id: str,
) -> Declaration | None:
    """Load all primitives for a scope from storage and assemble a Declaration.

    Returns None if no scope primitive is found.
    """
    rows = await storage.list_primitives(scope_id=scope_id)

    # Also get the scope itself (scope_id is None in storage for root scopes)
    scope_row = await storage.get_primitive(scope_id)
    if scope_row is None:
        return None

    scope_data = (
        json.loads(scope_row["data"]) if isinstance(scope_row["data"], str) else scope_row["data"]
    )
    scope = Scope.model_validate(scope_data)

    # Parse primitives by type
    archetypes: list[Archetype] = []
    domains: list[Domain] = []
    capabilities: list[Capability] = []
    views: list[View] = []
    policies: list[Policy] = []
    connectors: list[Connector] = []
    bindings: list[Binding] = []
    provenance_entries: list[ProvenanceEntry] = []

    for row in rows:
        ptype = row["type"]
        data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
        model_class = _PRIMITIVE_TYPE_MAP.get(ptype)
        if model_class is None:
            continue

        instance = model_class.model_validate(data)

        if ptype == "archetype":
            archetypes.append(instance)
        elif ptype == "domain":
            domains.append(instance)
        elif ptype == "capability":
            capabilities.append(instance)
        elif ptype == "view":
            views.append(instance)
        elif ptype == "policy":
            policies.append(instance)
        elif ptype == "connector":
            connectors.append(instance)
        elif ptype == "binding":
            bindings.append(instance)
        elif ptype == "provenance":
            provenance_entries.append(instance)

    # Load provenance from the provenance table too
    prov_rows = await storage.get_provenance(scope_id=scope_id)
    for prov_row in prov_rows:
        identity_row = await storage.get_identity(prov_row["actor_identity_id"])
        if identity_row:
            actor = HumanIdentity(
                email=identity_row["email"],
                display_name=identity_row["display_name"],
                title=identity_row.get("title"),
                department=identity_row.get("department"),
            )
        else:
            actor = HumanIdentity(email="unknown@unknown", display_name="Unknown")

        details = json.loads(prov_row["details"]) if prov_row["details"] else {}
        previous = (
            json.loads(prov_row["previous_state"]) if prov_row.get("previous_state") else None
        )

        provenance_entries.append(
            ProvenanceEntry(
                id=prov_row["id"],
                scope_id=prov_row["scope_id"],
                primitive_id=prov_row["primitive_id"],
                primitive_type=prov_row["primitive_type"],
                action=prov_row["action"],
                actor=actor,
                timestamp=datetime.fromisoformat(prov_row["timestamp"])
                if isinstance(prov_row["timestamp"], str)
                else prov_row["timestamp"],
                details=details,
                previous_state=previous,
            )
        )

    declaration = Declaration(
        id=_gen_id("decl"),
        version="0.1.0",
        scope=scope,
        archetypes=archetypes,
        domains=domains,
        capabilities=capabilities,
        views=views,
        policies=policies,
        connectors=connectors,
        bindings=bindings,
        provenance=provenance_entries,
        created_at=datetime.now(UTC),
    )
    declaration.compute_completion()

    return declaration


async def find_scope_for_identity(
    storage: StorageEngine,
    identity_email: str,
) -> str | None:
    """Find the most recent scope_id associated with an identity's primitives."""
    row = await storage.get_identity_by_email(identity_email)
    if not row:
        return None

    primitives = await storage.list_primitives_by_identity(row["id"])
    # Find scope primitives, or fall back to scope_id from any primitive
    for p in reversed(primitives):
        if p["type"] == "scope":
            return p["id"]

    for p in reversed(primitives):
        if p["scope_id"]:
            return p["scope_id"]

    return None
