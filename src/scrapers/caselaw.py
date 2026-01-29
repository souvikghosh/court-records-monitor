import logging
from typing import Optional
from urllib.parse import urlencode

import aiohttp

from .base import BaseScraper, SearchResult

logger = logging.getLogger(__name__)


class CaseLawScraper(BaseScraper):
    """
    Scraper for Case Law Access Project (case.law)

    The Caselaw Access Project provides free access to all official
    US court cases. Their API is free and requires no authentication
    for basic searches.
    """

    name = "caselaw"
    base_url = "https://case.law"
    api_url = "https://api.case.law/v1"

    async def search(self, term: str) -> list[SearchResult]:
        """Search Case Law Access Project API."""
        results = []

        params = {
            "search": term,
            "page_size": 20,
            "ordering": "-decision_date",
        }

        url = f"{self.api_url}/cases/?{urlencode(params)}"
        logger.info(f"[{self.name}] API request: {url}")

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
                        result = self._parse_result(item)
                        if result:
                            results.append(result)

        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] API request failed: {e}")
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")

        logger.info(f"[{self.name}] Found {len(results)} results for '{term}'")
        return results

    def _parse_result(self, item: dict) -> Optional[SearchResult]:
        """Parse an API result."""
        try:
            case_name = item.get("name_abbreviation") or item.get("name", "Unknown")

            # Get citations as case number
            citations = item.get("citations", [])
            case_number = citations[0].get("cite") if citations else str(item.get("id", ""))

            # Build URL
            case_url = item.get("frontend_url") or f"{self.base_url}/cases/{item.get('id', '')}"

            # Get court info
            court = item.get("court", {})
            court_name = court.get("name", "")

            return SearchResult(
                case_number=case_number,
                case_title=case_name,
                filing_date=item.get("decision_date"),
                case_type=court_name,
                parties=None,
                url=case_url
            )

        except Exception as e:
            logger.warning(f"[{self.name}] Error parsing result: {e}")
            return None
