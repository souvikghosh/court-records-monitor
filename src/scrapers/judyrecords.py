import logging
import re

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import BaseScraper, SearchResult

logger = logging.getLogger(__name__)


class JudyRecordsScraper(BaseScraper):
    """
    Scraper for JudyRecords.com

    JudyRecords is a free court records search engine that aggregates
    data from 760+ million US court cases.
    """

    name = "judyrecords"
    base_url = "https://www.judyrecords.com"

    async def search(self, term: str) -> list[SearchResult]:
        """Search JudyRecords for a term."""
        results = []
        page = await self.new_page()

        try:
            # Go to homepage first
            logger.info(f"[{self.name}] Navigating to homepage")
            await page.goto(self.base_url, wait_until="networkidle", timeout=30000)

            # Find and fill the search input
            search_input = await page.wait_for_selector(
                "input[placeholder*='search'], input[type='text'], input[name='q']",
                timeout=10000
            )
            await search_input.fill(term)

            # Click search button or press Enter
            search_button = await page.query_selector("button[type='submit'], input[type='submit'], button:has-text('Search')")
            if search_button:
                await search_button.click()
            else:
                await search_input.press("Enter")

            logger.info(f"[{self.name}] Searching for '{term}'")

            # Wait for navigation and results to load
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_timeout(2000)  # Extra time for JS

            # Check current URL to confirm search happened
            current_url = page.url
            logger.info(f"[{self.name}] Current URL: {current_url}")

            # Parse results
            results = await self._parse_results(page, term)

        except PlaywrightTimeout:
            logger.error(f"[{self.name}] Timeout searching for '{term}'")
            await self.screenshot(page, f"timeout_{term.replace(' ', '_')}")
        except Exception as e:
            logger.error(f"[{self.name}] Error searching for '{term}': {e}")
            await self.screenshot(page, f"error_{term.replace(' ', '_')}")
        finally:
            await page.close()

        logger.info(f"[{self.name}] Found {len(results)} results for '{term}'")
        return results

    async def _parse_results(self, page: Page, term: str) -> list[SearchResult]:
        """Parse search results from the page."""
        results = []

        # Take a screenshot to see what we got
        await self.screenshot(page, f"results_{term.replace(' ', '_')}")

        # Look for result links - JudyRecords shows results as list items
        # Try to find case links
        case_links = await page.query_selector_all("a[href*='/record/'], a[href*='/case/']")

        if case_links:
            logger.info(f"[{self.name}] Found {len(case_links)} case links")
            for link in case_links[:20]:
                result = await self._parse_link(link)
                if result:
                    results.append(result)
            return results

        # Fallback: look for any substantive links in the main content
        all_links = await page.query_selector_all("main a, .results a, #content a")
        for link in all_links[:30]:
            try:
                href = await link.get_attribute("href")
                text = await link.inner_text()

                # Skip navigation/footer links
                if not href or not text or len(text.strip()) < 10:
                    continue
                if any(skip in href.lower() for skip in ['terms', 'info', 'api', 'home', 'login', 'search']):
                    continue

                url = href if href.startswith("http") else f"{self.base_url}{href}"

                results.append(SearchResult(
                    case_number=self._extract_case_number(text) or "Unknown",
                    case_title=text.strip()[:200],
                    filing_date=None,
                    case_type=None,
                    parties=None,
                    url=url
                ))
            except Exception:
                continue

        return results

    async def _parse_link(self, link) -> SearchResult | None:
        """Parse a case link element."""
        try:
            href = await link.get_attribute("href")
            text = await link.inner_text()

            if not href or not text:
                return None

            url = href if href.startswith("http") else f"{self.base_url}{href}"

            return SearchResult(
                case_number=self._extract_case_number(text) or self._extract_case_number(href) or "Unknown",
                case_title=text.strip()[:200],
                filing_date=None,
                case_type=None,
                parties=None,
                url=url
            )
        except Exception as e:
            logger.warning(f"[{self.name}] Error parsing link: {e}")
            return None

    def _extract_case_number(self, text: str) -> str | None:
        """Extract case number from text."""
        if not text:
            return None

        patterns = [
            r"(\d{1,2}:\d{2}-\w{2}-\d+)",  # Federal: 1:23-cv-12345
            r"(\d{4}-\w{2,4}-\d+)",  # State: 2024-CV-12345
            r"(\d{2}-\d+-\w+)",  # 24-12345-CI
            r"Case\s*#?\s*:?\s*(\S+)",  # Case #12345
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
