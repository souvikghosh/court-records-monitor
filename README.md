# Court Records Monitor

Monitor public court records for new filings using browser automation.

## Features

- Automated monitoring of public court record websites
- SQLite database for tracking seen records
- Email/webhook notifications for new filings
- Configurable search queries (names, case numbers, keywords)
- Screenshot capture of new records
- Runs on schedule via cron

## Supported Courts

- **UNICOURT** - Aggregated federal and state records (free tier available)
- **CourtListener** - Free federal court opinions and PACER data
- **State Courts** - Extensible scrapers for state-specific sites

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copy `.env.example` to `.env` and configure:
- Search terms (names, companies to monitor)
- Notification settings (email/webhook)
- Check frequency

## Usage

```bash
# Run once
python main.py

# Run specific court
python main.py --court courtlistener

# Dry run (no notifications)
python main.py --dry-run
```

## License

MIT
