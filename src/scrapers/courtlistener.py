import logging
import re
from typing import Optional
from urllib.parse import urlencode

import aiohttp

from .base import BaseScraper, SearchResult

logger = logging.getLogger(__name__)


class CourtListenerScraper(BaseScraper):
    """
    Scraper for CourtListener.com using their free API.

    CourtListener provides a free API for searching court opinions
    and RECAP (PACER) data. No API key required for basic searches.
    """

    name = "courtlistener"
    base_url = "https://www.courtlistener.com"
    api_url = "https://www.courtlistener.com/api/rest/v4"

    async def search(self, term: str) -> list[SearchResult]:
        """Search CourtListener API for a term."""
        results = []

        try:
            # Search opinions via API
            opinion_results = await self._search_api(term, "opinions")
            results.extend(opinion_results)

            # Search RECAP dockets
            docket_results = await self._search_api(term, "dockets")
            results.extend(docket_results)

        except Exception as e:
            logger.error(f"[{self.name}] Error searching for '{term}': {e}")

        logger.info(f"[{self.name}] Found {len(results)} results for '{term}'")
        return results

    async def _search_api(self, term: str, endpoint: str) -> list[SearchResult]:
        """Search using the CourtListener API."""
        results = []

        params = {
            "q": term,
            "order_by": "-date_filed",
            "page_size": 20,
        }

        url = f"{self.api_url}/{endpoint}/?{urlencode(params)}"
        logger.info(f"[{self.name}] API request: {endpoint}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={"Accept": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"[{self.name}] API returned {response.status}")
                        return results

                    data = await response.json()

                    for item in data.get("results", []):
                        result = self._parse_result(item, endpoint)
                        if result:
                            results.append(result)

        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] API request failed: {e}")

        return results

    def _parse_result(self, item: dict, endpoint: str) -> Optional[SearchResult]:
        """Parse an API result into a SearchResult."""
        try:
            if endpoint == "opinions":
                case_name = item.get("case_name", "Unknown Case")
                case_number = self._extract_case_number(case_name) or str(item.get("id", ""))

                # Build URL
                absolute_url = item.get("absolute_url", "")
                url = f"{self.base_url}{absolute_url}" if absolute_url else self.base_url

                return SearchResult(
                    case_number=case_number,
                    case_title=case_name,
                    filing_date=item.get("date_filed"),
                    case_type="Opinion",
                    parties=None,
                    url=url
                )

            elif endpoint == "dockets":
                case_name = item.get("case_name", "Unknown Case")
                case_number = item.get("docket_number", str(item.get("id", "")))

                absolute_url = item.get("absolute_url", "")
                url = f"{self.base_url}{absolute_url}" if absolute_url else self.base_url

                return SearchResult(
                    case_number=case_number,
                    case_title=case_name,
                    filing_date=item.get("date_filed"),
                    case_type="Docket",
                    parties=None,
                    url=url
                )

        except Exception as e:
            logger.warning(f"[{self.name}] Error parsing result: {e}")

        return None

    def _extract_case_number(self, text: str) -> Optional[str]:
        """Extract case number from text."""
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
