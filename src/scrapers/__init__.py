from .base import BaseScraper, SearchResult
from .courtlistener import CourtListenerScraper
from .unicourt import UnicourtScraper
from .florida import FloridaCourtsScraper
from .judyrecords import JudyRecordsScraper
from .caselaw import CaseLawScraper

# Registry of all available scrapers
SCRAPERS = {
    "caselaw": CaseLawScraper,  # Free API, no auth required
    "judyrecords": JudyRecordsScraper,
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
    "JudyRecordsScraper",
    "CaseLawScraper",
    "SCRAPERS",
]
