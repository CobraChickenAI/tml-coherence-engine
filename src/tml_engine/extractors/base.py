"""Base extractor interface and intermediate extraction types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel


class ContentBlock(BaseModel):
    """A unit of extracted content with context."""

    content: str
    content_type: str  # "page", "comment", "issue", "description", "response"
    author: str | None = None
    created_at: datetime | None = None
    context: str  # Where in the source this came from
    url: str | None = None


class RawExtractionResult(BaseModel):
    """Intermediate format between extraction and structuring.
    All extractors produce this. The structurer converts it to TML primitives."""

    source_type: str  # "confluence", "jira", "web", "interview"
    source_identifier: str  # URL, space key, project key, etc.
    content_blocks: list[ContentBlock]
    metadata: dict
    extracted_at: datetime


class BaseExtractor(ABC):
    @abstractmethod
    async def extract(self, config: dict) -> RawExtractionResult:
        """Extract content from a source."""
        ...

    @abstractmethod
    async def list_available(self) -> list[dict]:
        """List available sources the user can choose from."""
        ...
