import logging
import re
from urllib.parse import urlencode

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, SearchResult

logger = logging.getLogger(__name__)


class CourtListenerScraper(BaseScraper):
    """
    Scraper for CourtListener.com

    CourtListener is a free, open database of court opinions,
    federal filings (via RECAP), and oral arguments.
    """

    name = "courtlistener"
    base_url = "https://www.courtlistener.com"

    async def search(self, term: str) -> list[SearchResult]:
        """Search CourtListener for a term."""
        results = []
        page = await self.new_page()

        try:
            # Search opinions
            opinion_results = await self._search_opinions(page, term)
            results.extend(opinion_results)

            # Search RECAP (federal district court filings)
            recap_results = await self._search_recap(page, term)
            results.extend(recap_results)

        except PlaywrightTimeout:
            logger.error(f"[{self.name}] Timeout searching for '{term}'")
        except Exception as e:
            logger.error(f"[{self.name}] Error searching for '{term}': {e}")
        finally:
            await page.close()

        logger.info(f"[{self.name}] Found {len(results)} results for '{term}'")
        return results

    async def _search_opinions(self, page: Page, term: str) -> list[SearchResult]:
        """Search court opinions."""
        results = []

        params = {
            "q": term,
            "type": "o",  # opinions
            "order_by": "dateFiled desc",
        }
        url = f"{self.base_url}/?{urlencode(params)}"

        logger.info(f"[{self.name}] Searching opinions: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for results to load
        try:
            await page.wait_for_selector("article.v-card", timeout=10000)
        except PlaywrightTimeout:
            logger.info(f"[{self.name}] No opinion results found for '{term}'")
            return results

        # Parse results
        articles = await page.query_selector_all("article.v-card")

        for article in articles[:20]:  # Limit to first 20
            try:
                # Get case title and link
                title_el = await article.query_selector("h3 a")
                if not title_el:
                    continue

                title = await title_el.inner_text()
                href = await title_el.get_attribute("href")
                url = f"{self.base_url}{href}" if href.startswith("/") else href

                # Get court and date
                meta_el = await article.query_selector(".bottom")
                meta_text = await meta_el.inner_text() if meta_el else ""

                # Parse date from meta (format varies)
                filing_date = None
                date_match = re.search(r"(\w+ \d{1,2}, \d{4})", meta_text)
                if date_match:
                    filing_date = date_match.group(1)

                # Extract case number from title if present
                case_number = self._extract_case_number(title) or href.split("/")[-2]

                results.append(SearchResult(
                    case_number=case_number,
                    case_title=title.strip(),
                    filing_date=filing_date,
                    case_type="Opinion",
                    parties=None,
                    url=url
                ))

            except Exception as e:
                logger.warning(f"[{self.name}] Error parsing opinion result: {e}")
                continue

        return results

    async def _search_recap(self, page: Page, term: str) -> list[SearchResult]:
        """Search RECAP archive (federal district court filings)."""
        results = []

        params = {
            "q": term,
            "type": "r",  # RECAP
            "order_by": "dateFiled desc",
        }
        url = f"{self.base_url}/?{urlencode(params)}"

        logger.info(f"[{self.name}] Searching RECAP: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Wait for results
        try:
            await page.wait_for_selector("article.v-card", timeout=10000)
        except PlaywrightTimeout:
            logger.info(f"[{self.name}] No RECAP results found for '{term}'")
            return results

        # Parse results
        articles = await page.query_selector_all("article.v-card")

        for article in articles[:20]:  # Limit to first 20
            try:
                # Get case title and link
                title_el = await article.query_selector("h3 a")
                if not title_el:
                    continue

                title = await title_el.inner_text()
                href = await title_el.get_attribute("href")
                url = f"{self.base_url}{href}" if href.startswith("/") else href

                # Get filing info
                meta_el = await article.query_selector(".bottom")
                meta_text = await meta_el.inner_text() if meta_el else ""

                # Parse date
                filing_date = None
                date_match = re.search(r"(\w+ \d{1,2}, \d{4})", meta_text)
                if date_match:
                    filing_date = date_match.group(1)

                # Parse case number
                case_number = self._extract_case_number(title)
                if not case_number:
                    # Try from URL
                    case_number = href.split("/")[-2] if "/" in href else "Unknown"

                results.append(SearchResult(
                    case_number=case_number,
                    case_title=title.strip(),
                    filing_date=filing_date,
                    case_type="RECAP/PACER",
                    parties=None,
                    url=url
                ))

            except Exception as e:
                logger.warning(f"[{self.name}] Error parsing RECAP result: {e}")
                continue

        return results

    def _extract_case_number(self, text: str) -> str | None:
        """Extract case number from text."""
        # Common federal case number patterns
        patterns = [
            r"(\d{1,2}:\d{2}-\w{2}-\d+)",  # 1:23-cv-12345
            r"(\d{2}-\d+)",  # 23-12345
            r"No\.\s*(\S+)",  # No. 12345
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None
