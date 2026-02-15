"""Tests for extractor base types."""

from datetime import UTC, datetime

from tml_engine.extractors.base import ContentBlock, RawExtractionResult


class TestContentBlock:
    def test_create(self) -> None:
        block = ContentBlock(
            content="This team evaluates carriers based on safety metrics.",
            content_type="page",
            author="Michael",
            context="Confluence > Engineering Wiki > Carrier Evaluation",
            url="https://wiki.example.com/carrier-eval",
        )
        assert block.content_type == "page"
        assert block.author == "Michael"

    def test_minimal(self) -> None:
        block = ContentBlock(
            content="Some content",
            content_type="description",
            context="Jira > PLATFORM-123",
        )
        assert block.url is None
        assert block.author is None


class TestRawExtractionResult:
    def test_create(self) -> None:
        result = RawExtractionResult(
            source_type="web",
            source_identifier="https://example.com",
            content_blocks=[
                ContentBlock(
                    content="Page content",
                    content_type="page",
                    context="Homepage",
                ),
            ],
            metadata={"pages_crawled": 5},
            extracted_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert result.source_type == "web"
        assert len(result.content_blocks) == 1
        assert result.metadata["pages_crawled"] == 5

    def test_serialization(self) -> None:
        result = RawExtractionResult(
            source_type="interview",
            source_identifier="session-001",
            content_blocks=[],
            metadata={},
            extracted_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        data = result.model_dump(mode="json")
        restored = RawExtractionResult.model_validate(data)
        assert restored.source_type == "interview"
