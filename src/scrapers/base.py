from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from src.database import CourtRecord
from src.config import HEADLESS, SCREENSHOTS_DIR

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Raw search result before database storage."""
    case_number: str
    case_title: str
    filing_date: Optional[str]
    case_type: Optional[str]
    parties: Optional[str]
    url: str


class BaseScraper(ABC):
    """Abstract base class for court record scrapers."""

    # Override in subclasses
    name: str = "base"
    base_url: str = ""

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self) -> None:
        """Start the browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        logger.info(f"[{self.name}] Browser started")

    async def stop(self) -> None:
        """Stop the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"[{self.name}] Browser stopped")

    async def new_page(self) -> Page:
        """Create a new browser page."""
        return await self._context.new_page()

    async def screenshot(self, page: Page, name: str) -> Path:
        """Take a screenshot of the current page."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{name}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        await page.screenshot(path=filepath, full_page=True)
        logger.info(f"[{self.name}] Screenshot saved: {filepath}")
        return filepath

    @abstractmethod
    async def search(self, term: str) -> list[SearchResult]:
        """
        Search for court records matching the term.

        Args:
            term: Name, company, or case number to search

        Returns:
            List of SearchResult objects
        """
        pass

    def to_court_record(self, result: SearchResult, search_term: str) -> CourtRecord:
        """Convert a SearchResult to a CourtRecord."""
        now = datetime.utcnow()
        return CourtRecord(
            id=None,
            court=self.name,
            case_number=result.case_number,
            case_title=result.case_title,
            filing_date=result.filing_date,
            case_type=result.case_type,
            parties=result.parties,
            url=result.url,
            search_term=search_term,
            first_seen=now,
            last_seen=now,
            notified=False
        )
