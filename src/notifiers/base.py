from abc import ABC, abstractmethod
import logging

from src.database import CourtRecord

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Abstract base class for notification handlers."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this notifier is properly configured."""
        pass

    @abstractmethod
    async def notify(self, records: list[CourtRecord]) -> bool:
        """
        Send notification for new records.

        Args:
            records: List of new court records to notify about

        Returns:
            True if notification was sent successfully
        """
        pass

    def format_record(self, record: CourtRecord) -> str:
        """Format a single record for display."""
        lines = [
            f"**{record.case_title}**",
            f"Case #: {record.case_number}",
            f"Court: {record.court}",
        ]

        if record.filing_date:
            lines.append(f"Filed: {record.filing_date}")
        if record.case_type:
            lines.append(f"Type: {record.case_type}")

        lines.append(f"Search term: {record.search_term}")
        lines.append(f"URL: {record.url}")

        return "\n".join(lines)
