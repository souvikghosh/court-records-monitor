import logging
import re
from urllib.parse import urlencode

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, SearchResult

logger = logging.getLogger(__name__)


class FloridaCourtsScraper(BaseScraper):
    """
    Scraper for Florida State Courts

    Uses the Florida Courts e-filing portal and public records search.
    """

    name = "florida_courts"
    base_url = "https://www.flcourts.gov"
    search_url = "https://hover.flcourts.gov/search"

    async def search(self, term: str) -> list[SearchResult]:
        """Search Florida courts for a term."""
        results = []
        page = await self.new_page()

        try:
            logger.info(f"[{self.name}] Searching for '{term}'")

            # Florida has a statewide search portal
            await page.goto(self.search_url, wait_until="networkidle", timeout=30000)

            # Look for search input
            search_input = await page.query_selector(
                "input[type='search'], input[name='q'], input[placeholder*='Search'], #search"
            )

            if search_input:
                await search_input.fill(term)
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=15000)

                # Parse results based on page structure
                results = await self._parse_results(page)
            else:
                logger.warning(f"[{self.name}] Could not find search input")

        except PlaywrightTimeout:
            logger.error(f"[{self.name}] Timeout searching for '{term}'")
        except Exception as e:
            logger.error(f"[{self.name}] Error searching for '{term}': {e}")
        finally:
            await page.close()

        logger.info(f"[{self.name}] Found {len(results)} results for '{term}'")
        return results

    async def _parse_results(self, page: Page) -> list[SearchResult]:
        """Parse search results from the page."""
        results = []

        # Try common result container selectors
        selectors = [
            "table tbody tr",
            ".search-results .result",
            ".case-list .case-item",
            "article.case",
            ".results-list li"
        ]

        for selector in selectors:
            items = await page.query_selector_all(selector)
            if items:
                for item in items[:20]:
                    result = await self._parse_result_item(item, selector)
                    if result:
                        results.append(result)
                break

        return results

    async def _parse_result_item(self, item, selector: str) -> SearchResult | None:
        """Parse a single result item."""
        try:
            if "tr" in selector:
                # Table row format
                cells = await item.query_selector_all("td")
                if len(cells) >= 3:
                    case_number = await cells[0].inner_text()
                    case_title = await cells[1].inner_text()

                    link = await item.query_selector("a")
                    href = await link.get_attribute("href") if link else ""
                    url = href if href.startswith("http") else f"{self.base_url}{href}"

                    return SearchResult(
                        case_number=case_number.strip(),
                        case_title=case_title.strip(),
                        filing_date=await cells[2].inner_text() if len(cells) > 2 else None,
                        case_type=await cells[3].inner_text() if len(cells) > 3 else None,
                        parties=None,
                        url=url
                    )
            else:
                # Generic item format
                link = await item.query_selector("a")
                if not link:
                    return None

                title = await link.inner_text()
                href = await link.get_attribute("href")
                url = href if href.startswith("http") else f"{self.base_url}{href}"

                # Try to extract case number
                case_number = self._extract_case_number(title)

                return SearchResult(
                    case_number=case_number or "Unknown",
                    case_title=title.strip(),
                    filing_date=None,
                    case_type=None,
                    parties=None,
                    url=url
                )

        except Exception as e:
            logger.warning(f"[{self.name}] Error parsing result: {e}")
            return None

    def _extract_case_number(self, text: str) -> str | None:
        """Extract Florida case number from text."""
        # Florida case number patterns
        patterns = [
            r"(\d{4}-\w{2}-\d+)",  # 2024-CA-12345
            r"(\d{2}-\d+-\w+)",    # 24-12345-CI
            r"Case\s*#?\s*(\S+)",  # Case #12345
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
