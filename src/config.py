import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project root
ROOT_DIR = Path(__file__).parent.parent

# Search terms
SEARCH_TERMS = [
    term.strip()
    for term in os.getenv("SEARCH_TERMS", "").split(",")
    if term.strip()
]

# Database
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", ROOT_DIR / "data" / "records.db"))

# Email notifications
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")

# Webhooks
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Browser
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
SCREENSHOT_ON_NEW = os.getenv("SCREENSHOT_ON_NEW", "true").lower() == "true"
SCREENSHOTS_DIR = ROOT_DIR / "screenshots"

# Ensure directories exist
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
