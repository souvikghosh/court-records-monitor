import logging

import aiohttp

from src.config import DISCORD_WEBHOOK_URL
from src.database import CourtRecord
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class DiscordNotifier(BaseNotifier):
    """Send notifications via Discord webhook."""

    name = "discord"

    def is_configured(self) -> bool:
        return bool(DISCORD_WEBHOOK_URL)

    async def notify(self, records: list[CourtRecord]) -> bool:
        if not self.is_configured():
            logger.warning(f"[{self.name}] Not configured, skipping")
            return False

        if not records:
            return True

        try:
            # Discord has a 2000 char limit per message, so batch if needed
            embeds = []

            for record in records[:10]:  # Discord allows max 10 embeds
                embed = {
                    "title": record.case_title[:256],  # Max title length
                    "url": record.url,
                    "color": 0x5865F2,  # Discord blurple
                    "fields": [
                        {
                            "name": "Case Number",
                            "value": record.case_number,
                            "inline": True
                        },
                        {
                            "name": "Court",
                            "value": record.court,
                            "inline": True
                        },
                        {
                            "name": "Search Term",
                            "value": record.search_term,
                            "inline": True
                        },
                    ]
                }

                if record.filing_date:
                    embed["fields"].append({
                        "name": "Filing Date",
                        "value": record.filing_date,
                        "inline": True
                    })

                if record.case_type:
                    embed["fields"].append({
                        "name": "Case Type",
                        "value": record.case_type,
                        "inline": True
                    })

                embeds.append(embed)

            payload = {
                "content": f"**Court Records Alert:** Found {len(records)} new filing(s)",
                "embeds": embeds
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    DISCORD_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status < 300:
                        logger.info(f"[{self.name}] Discord notification sent")
                        return True
                    else:
                        text = await response.text()
                        logger.error(
                            f"[{self.name}] Discord failed: {response.status} - {text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"[{self.name}] Discord error: {e}")
            return False
