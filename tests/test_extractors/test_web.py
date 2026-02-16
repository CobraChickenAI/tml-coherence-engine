"""Tests for the web scrape extractor."""

from __future__ import annotations

import pytest

from tml_engine.extractors.web import ScrapeConfig, WebExtractor


class TestScrapeConfig:
    def test_default_config(self) -> None:
        config = ScrapeConfig.default("https://example.com")
        assert config.base_url == "https://example.com"
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.respect_robots is True
        assert len(config.primary_selectors) > 0
        assert len(config.strip_selectors) > 0

    def test_from_dict(self) -> None:
        data = {
            "target": {
                "base_url": "https://test.com",
                "max_depth": 2,
                "max_pages": 50,
                "respect_robots": False,
            },
            "include_patterns": ["/about*"],
            "exclude_patterns": ["*.pdf"],
            "content_selectors": {
                "primary": ["main"],
                "strip": ["nav"],
            },
        }
        config = ScrapeConfig.from_dict(data)
        assert config.base_url == "https://test.com"
        assert config.max_depth == 2
        assert config.max_pages == 50
        assert config.respect_robots is False
        assert config.include_patterns == ["/about*"]
        assert config.exclude_patterns == ["*.pdf"]
        assert config.primary_selectors == ["main"]
        assert config.strip_selectors == ["nav"]


class TestWebExtractor:
    def test_init(self) -> None:
        extractor = WebExtractor()
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_extract_requires_base_url(self) -> None:
        extractor = WebExtractor()
        with pytest.raises(ValueError, match="base_url is required"):
            await extractor.extract({})

    @pytest.mark.asyncio
    async def test_list_available_returns_empty(self) -> None:
        extractor = WebExtractor()
        result = await extractor.list_available()
        assert result == []

    def test_should_crawl_filters(self) -> None:
        config = ScrapeConfig.from_dict(
            {
                "target": {"base_url": "https://example.com"},
                "include_patterns": ["/about*"],
                "exclude_patterns": ["*.pdf"],
            }
        )
        extractor = WebExtractor(config=config)

        # Should crawl base URL even if it doesn't match include pattern
        assert extractor._should_crawl("https://example.com") is True

        # Should crawl matching include pattern
        assert extractor._should_crawl("https://example.com/about") is True

        # Should not crawl non-matching
        assert extractor._should_crawl("https://example.com/contact") is False

        # Should not crawl excluded
        assert extractor._should_crawl("https://example.com/about/file.pdf") is False

        # Should not crawl different domain
        assert extractor._should_crawl("https://other.com/about") is False

    def test_should_crawl_visited(self) -> None:
        config = ScrapeConfig.default("https://example.com")
        extractor = WebExtractor(config=config)
        extractor._visited.add("https://example.com/page1")
        assert extractor._should_crawl("https://example.com/page1") is False

    def test_should_crawl_max_pages(self) -> None:
        config = ScrapeConfig.from_dict(
            {
                "target": {"base_url": "https://example.com", "max_pages": 0},
            }
        )
        extractor = WebExtractor(config=config)
        assert extractor._should_crawl("https://example.com") is False

    def test_extract_text_from_html(self) -> None:
        from bs4 import BeautifulSoup

        config = ScrapeConfig.default("https://example.com")
        extractor = WebExtractor(config=config)

        html = "<html><body><main><p>Hello world</p></main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = extractor._extract_text(soup)
        assert "Hello world" in text

    def test_extract_text_fallback(self) -> None:
        from bs4 import BeautifulSoup

        config = ScrapeConfig.default("https://example.com")
        extractor = WebExtractor(config=config)

        html = "<html><body><div>Fallback content</div></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = extractor._extract_text(soup)
        assert "Fallback content" in text
