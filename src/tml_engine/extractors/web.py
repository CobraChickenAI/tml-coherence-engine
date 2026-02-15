"""Web scrape extractor — crawls a website and extracts content blocks."""

from __future__ import annotations

import fnmatch
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from bs4 import BeautifulSoup

from tml_engine.extractors.base import BaseExtractor, ContentBlock, RawExtractionResult

_DEFAULT_TEMPLATE = Path(__file__).parent.parent.parent.parent / "templates" / "web_scrape" / "default.yaml"


class ScrapeConfig:
    """Parsed web scrape configuration."""

    def __init__(self, config: dict) -> None:
        target = config.get("target", {})
        self.base_url: str = target.get("base_url", "")
        self.max_depth: int = target.get("max_depth", 3)
        self.max_pages: int = target.get("max_pages", 100)
        self.respect_robots: bool = target.get("respect_robots", True)

        self.include_patterns: list[str] = config.get("include_patterns", [])
        self.exclude_patterns: list[str] = config.get("exclude_patterns", [])

        selectors = config.get("content_selectors", {})
        self.primary_selectors: list[str] = selectors.get(
            "primary", ["main", "article", ".content", "#content"]
        )
        self.strip_selectors: list[str] = selectors.get(
            "strip", ["nav", "footer", "header", ".sidebar", "script", "style"]
        )

    @classmethod
    def from_yaml(cls, path: Path) -> ScrapeConfig:
        data = yaml.safe_load(path.read_text())
        return cls(data)

    @classmethod
    def default(cls, base_url: str) -> ScrapeConfig:
        if _DEFAULT_TEMPLATE.exists():
            config = cls.from_yaml(_DEFAULT_TEMPLATE)
        else:
            config = cls({})
        config.base_url = base_url
        return config


class WebExtractor(BaseExtractor):
    """Extracts content from a website via crawling."""

    def __init__(self, config: ScrapeConfig | None = None) -> None:
        self._config = config
        self._visited: set[str] = set()
        self._content_blocks: list[ContentBlock] = []

    async def extract(self, config: dict) -> RawExtractionResult:
        """Crawl a website and extract content blocks.

        config must contain 'base_url' at minimum. Optional keys:
        'template_path', 'max_depth', 'max_pages'.
        """
        base_url = config.get("base_url", "")
        if not base_url:
            raise ValueError("base_url is required in config")

        if self._config is None:
            template_path = config.get("template_path")
            if template_path:
                self._config = ScrapeConfig.from_yaml(Path(template_path))
                self._config.base_url = base_url
            else:
                self._config = ScrapeConfig.default(base_url)

        if "max_depth" in config:
            self._config.max_depth = config["max_depth"]
        if "max_pages" in config:
            self._config.max_pages = config["max_pages"]

        self._visited.clear()
        self._content_blocks.clear()

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers={"User-Agent": "TML-Coherence-Engine/0.1"},
        ) as client:
            if self._config.respect_robots:
                await self._check_robots(client)
            await self._crawl(client, base_url, depth=0)

        return RawExtractionResult(
            source_type="web",
            source_identifier=base_url,
            content_blocks=self._content_blocks,
            metadata={
                "pages_crawled": len(self._visited),
                "max_depth": self._config.max_depth,
                "max_pages": self._config.max_pages,
            },
            extracted_at=datetime.now(UTC),
        )

    async def list_available(self) -> list[dict]:
        """Not applicable for web scraping — returns empty list."""
        return []

    async def _check_robots(self, client: httpx.AsyncClient) -> None:
        """Fetch and parse robots.txt (best-effort)."""
        parsed = urlparse(self._config.base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                self._robots_content = resp.text
        except httpx.HTTPError:
            pass  # robots.txt unavailable — proceed

    def _should_crawl(self, url: str) -> bool:
        """Check if a URL should be crawled based on include/exclude patterns."""
        if url in self._visited:
            return False
        if len(self._visited) >= self._config.max_pages:
            return False

        parsed = urlparse(url)
        base_parsed = urlparse(self._config.base_url)

        # Must be same domain
        if parsed.netloc != base_parsed.netloc:
            return False

        path = parsed.path

        # Check exclude patterns
        for pattern in self._config.exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False

        # If include patterns exist, URL must match at least one
        if self._config.include_patterns:
            matched = any(
                fnmatch.fnmatch(path, p) for p in self._config.include_patterns
            )
            if not matched:
                # Also allow the base URL itself
                if url.rstrip("/") != self._config.base_url.rstrip("/"):
                    return False

        return True

    async def _crawl(
        self, client: httpx.AsyncClient, url: str, depth: int
    ) -> None:
        """Recursively crawl pages breadth-first."""
        if depth > self._config.max_depth:
            return
        if not self._should_crawl(url):
            return

        self._visited.add(url)

        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                return
        except httpx.HTTPError:
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip noise elements
        for selector in self._config.strip_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Extract main content
        text = self._extract_text(soup)
        if text.strip():
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            self._content_blocks.append(
                ContentBlock(
                    content=text,
                    content_type="page",
                    context=title or url,
                    url=url,
                )
            )

        # Find links to crawl
        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute = urljoin(url, href)
            # Strip fragment
            absolute = absolute.split("#")[0]
            if absolute not in self._visited:
                links.append(absolute)

        # Crawl discovered links
        for link in links:
            await self._crawl(client, link, depth + 1)

    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract text content from the page, prioritizing primary selectors."""
        for selector in self._config.primary_selectors:
            elements = soup.select(selector)
            if elements:
                texts = [el.get_text(separator="\n", strip=True) for el in elements]
                return "\n\n".join(texts)

        # Fallback: use body text
        body = soup.find("body")
        if body:
            return body.get_text(separator="\n", strip=True)
        return soup.get_text(separator="\n", strip=True)
