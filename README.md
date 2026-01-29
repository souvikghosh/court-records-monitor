# Court Records Monitor

Monitor public court records for new filings using browser automation.

## Features

- Automated monitoring of public court record websites
- SQLite database for tracking seen records
- Email/webhook/Discord notifications for new filings
- Configurable search queries (names, case numbers, companies)
- Screenshot capture of new records
- Runs on schedule via cron

## Supported Courts

| Court | Type | Status |
|-------|------|--------|
| **JudyRecords** | 760M+ US court cases | Working |
| **CourtListener** | Federal opinions/PACER | Requires API key |
| **Unicourt** | Federal + State aggregator | Requires account |
| **Florida Courts** | Florida state courts | Experimental |
| **Case Law Access** | Historical cases | API deprecated |

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/court-records-monitor.git
cd court-records-monitor

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with your search terms and notification settings

# Run
python main.py --dry-run  # Test without notifications
python main.py            # Full run with notifications
```

## Configuration

Edit `.env`:

```bash
# Search terms (comma-separated names/companies to monitor)
SEARCH_TERMS=John Doe,Acme Corporation,Jane Smith

# Notifications (optional - configure at least one)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app_password
NOTIFY_EMAIL=alerts@example.com
```

## Usage

```bash
# Run all courts
python main.py

# Run specific court only
python main.py --court judyrecords

# Dry run (no notifications, no screenshots)
python main.py --dry-run

# List available courts
python main.py --list-courts
```

## Cron Setup

Run daily at 9 AM:

```bash
crontab -e

# Add this line (adjust paths):
0 9 * * * cd /path/to/court-records-monitor && ./venv/bin/python main.py >> logs/cron.log 2>&1
```

## Project Structure

```
court-records-monitor/
├── main.py                 # Entry point
├── src/
│   ├── config.py           # Configuration
│   ├── database.py         # SQLite storage
│   ├── scrapers/           # Court scrapers
│   │   ├── base.py         # Base scraper class
│   │   ├── judyrecords.py  # JudyRecords.com
│   │   ├── courtlistener.py
│   │   └── ...
│   └── notifiers/          # Notification handlers
│       ├── discord.py
│       ├── email.py
│       └── webhook.py
├── data/                   # SQLite database
├── screenshots/            # Captured screenshots
└── logs/                   # Log files
```

## How It Works

1. **Scrape** - Browser automation searches each court site for your terms
2. **Dedupe** - New records are compared against database
3. **Notify** - New findings trigger Discord/email/webhook alerts
4. **Store** - All records saved to SQLite for history

## License

MIT
