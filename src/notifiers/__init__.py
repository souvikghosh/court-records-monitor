from .base import BaseNotifier
from .email import EmailNotifier
from .webhook import WebhookNotifier
from .discord import DiscordNotifier

# All available notifiers
NOTIFIERS = [
    EmailNotifier(),
    WebhookNotifier(),
    DiscordNotifier(),
]


async def notify_all(records: list) -> dict[str, bool]:
    """
    Send notifications through all configured notifiers.

    Returns:
        Dict mapping notifier name to success status
    """
    results = {}

    for notifier in NOTIFIERS:
        if notifier.is_configured():
            results[notifier.name] = await notifier.notify(records)

    return results


__all__ = [
    "BaseNotifier",
    "EmailNotifier",
    "WebhookNotifier",
    "DiscordNotifier",
    "NOTIFIERS",
    "notify_all",
]
