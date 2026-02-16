"""Provenance generation for the confirmation surface.

Every confirm, correct, or flag action MUST produce a ProvenanceEntry.
This module provides the shared logic used by all confirmation screens.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from tml_engine.models.identity import (
    ConfirmationRecord,
    ConfirmationStatus,
    HumanIdentity,
)
from tml_engine.models.primitives import ProvenanceEntry


def make_confirmation_record(
    status: ConfirmationStatus,
    actor: HumanIdentity,
    original_text: str | None = None,
    corrected_text: str | None = None,
    flag_reason: str | None = None,
) -> ConfirmationRecord:
    """Create a ConfirmationRecord for a primitive."""
    return ConfirmationRecord(
        status=status,
        confirmed_by=actor,
        confirmed_at=datetime.now(UTC),
        original_text=original_text,
        corrected_text=corrected_text,
        flag_reason=flag_reason,
    )


def make_provenance_entry(
    scope_id: str,
    primitive_id: str,
    primitive_type: str,
    action: str,
    actor: HumanIdentity,
    details: dict | None = None,
    previous_state: dict | None = None,
) -> ProvenanceEntry:
    """Create a ProvenanceEntry for a confirmation action."""
    return ProvenanceEntry(
        id=f"prov-{uuid.uuid4().hex[:8]}",
        scope_id=scope_id,
        primitive_id=primitive_id,
        primitive_type=primitive_type,
        action=action,
        actor=actor,
        timestamp=datetime.now(UTC),
        details=details or {},
        previous_state=previous_state,
    )
