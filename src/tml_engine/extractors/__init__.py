"""Extractors — produce RawExtractionResult from various sources."""

from tml_engine.extractors.base import BaseExtractor, ContentBlock, RawExtractionResult
from tml_engine.extractors.web import WebExtractor

__all__ = [
    "BaseExtractor",
    "ContentBlock",
    "RawExtractionResult",
    "WebExtractor",
]
