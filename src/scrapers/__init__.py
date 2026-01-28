from .base import BaseScraper, SearchResult
from .courtlistener import CourtListenerScraper
from .unicourt import UnicourtScraper
from .florida import FloridaCourtsScraper

# Registry of all available scrapers
SCRAPERS = {
    "courtlistener": CourtListenerScraper,
    "unicourt": UnicourtScraper,
    "florida": FloridaCourtsScraper,
}

__all__ = [
    "BaseScraper",
    "SearchResult",
    "CourtListenerScraper",
    "UnicourtScraper",
    "FloridaCourtsScraper",
    "SCRAPERS",
]
