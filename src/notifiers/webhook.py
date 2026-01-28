import logging
import json

import aiohttp

from src.config import WEBHOOK_URL
from src.database import CourtRecord
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class WebhookNotifier(BaseNotifier):
    """Send notifications via generic webhook (POST JSON)."""

    name = "webhook"

    def is_configured(self) -> bool:
        return bool(WEBHOOK_URL)

    async def notify(self, records: list[CourtRecord]) -> bool:
        if not self.is_configured():
            logger.warning(f"[{self.name}] Not configured, skipping")
            return False

        if not records:
            return True

        try:
            payload = {
                "event": "new_court_records",
                "count": len(records),
                "records": [
                    {
                        "court": r.court,
                        "case_number": r.case_number,
                        "case_title": r.case_title,
                        "filing_date": r.filing_date,
                        "case_type": r.case_type,
                        "parties": r.parties,
                        "url": r.url,
                        "search_term": r.search_term,
                        "first_seen": r.first_seen.isoformat(),
                    }
                    for r in records
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    WEBHOOK_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status < 300:
                        logger.info(f"[{self.name}] Webhook sent successfully")
                        return True
                    else:
                        logger.error(
                            f"[{self.name}] Webhook failed: {response.status}"
                        )
                        return False

        except Exception as e:
            logger.error(f"[{self.name}] Webhook error: {e}")
            return False
