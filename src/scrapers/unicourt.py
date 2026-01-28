import logging
import json
from urllib.parse import urlencode

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, SearchResult

logger = logging.getLogger(__name__)


class UnicourtScraper(BaseScraper):
    """
    Scraper for Unicourt.com

    Unicourt aggregates court records from federal and state courts.
    Free tier allows basic searches.
    """

    name = "unicourt"
    base_url = "https://unicourt.com"

    async def search(self, term: str) -> list[SearchResult]:
        """Search Unicourt for a term."""
        results = []
        page = await self.new_page()

        try:
            # Navigate to search
            search_url = f"{self.base_url}/search?q={urlencode({'': term})[1:]}"
            logger.info(f"[{self.name}] Searching: {search_url}")

            await page.goto(search_url, wait_until="networkidle", timeout=30000)

            # Check for cookie consent or popups
            try:
                close_btn = await page.query_selector("[aria-label='Close']")
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

            # Wait for results
            try:
                await page.wait_for_selector(
                    "[data-testid='case-card'], .case-card, .search-result",
                    timeout=15000
                )
            except PlaywrightTimeout:
                logger.info(f"[{self.name}] No results found for '{term}'")
                return results

            # Parse results - Unicourt uses various CSS classes
            cards = await page.query_selector_all(
                "[data-testid='case-card'], .case-card, .search-result-item"
            )

            if not cards:
                # Try alternative selectors
                cards = await page.query_selector_all("article, .result-item")

            for card in cards[:20]:  # Limit results
                try:
                    result = await self._parse_card(card)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.warning(f"[{self.name}] Error parsing card: {e}")
                    continue

        except PlaywrightTimeout:
            logger.error(f"[{self.name}] Timeout searching for '{term}'")
        except Exception as e:
            logger.error(f"[{self.name}] Error searching for '{term}': {e}")
        finally:
            await page.close()

        logger.info(f"[{self.name}] Found {len(results)} results for '{term}'")
        return results

    async def _parse_card(self, card) -> SearchResult | None:
        """Parse a case card element."""
        # Try to get title/link
        title_el = await card.query_selector("a[href*='/case/'], h3 a, .case-title a")
        if not title_el:
            return None

        title = await title_el.inner_text()
        href = await title_el.get_attribute("href")

        if not href:
            return None

        url = href if href.startswith("http") else f"{self.base_url}{href}"

        # Try to extract case number from URL or title
        case_number = "Unknown"
        if "/case/" in href:
            # URL format: /case/STATE/CASENO/...
            parts = href.split("/")
            if len(parts) >= 4:
                case_number = parts[3]

        # Get case type
        type_el = await card.query_selector(".case-type, [data-testid='case-type']")
        case_type = await type_el.inner_text() if type_el else None

        # Get date
        date_el = await card.query_selector(".date, [data-testid='date'], time")
        filing_date = await date_el.inner_text() if date_el else None

        # Get parties
        parties_el = await card.query_selector(".parties, [data-testid='parties']")
        parties = await parties_el.inner_text() if parties_el else None

        return SearchResult(
            case_number=case_number,
            case_title=title.strip(),
            filing_date=filing_date,
            case_type=case_type,
            parties=parties,
            url=url
        )
