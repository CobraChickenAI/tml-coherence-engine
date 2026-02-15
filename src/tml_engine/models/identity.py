"""Foundation types: identity, confirmation, and extraction source."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ConfirmationStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    FLAGGED = "flagged"


class HumanIdentity(BaseModel):
    """Anchored to a real-world identity provider (Google Workspace, etc.).
    Not a TML primitive — this is the real-world anchor that Archetypes reference."""

    email: str
    display_name: str
    title: str | None = None
    department: str | None = None
    workspace_id: str | None = None


class ConfirmationRecord(BaseModel):
    """Tracks who confirmed what and when. Feeds into Provenance."""

    status: ConfirmationStatus
    confirmed_by: HumanIdentity
    confirmed_at: datetime
    original_text: str | None = None
    corrected_text: str | None = None
    flag_reason: str | None = None


class ExtractionSource(BaseModel):
    """Where a primitive was extracted from. Feeds into Provenance."""

    source_type: str  # "confluence", "jira", "web", "interview"
    source_identifier: str  # URL, space key, project key, etc.
    extracted_at: datetime
