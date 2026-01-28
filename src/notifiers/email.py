import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL
from src.database import CourtRecord
from .base import BaseNotifier

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Send notifications via email."""

    name = "email"

    def is_configured(self) -> bool:
        return all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, NOTIFY_EMAIL])

    async def notify(self, records: list[CourtRecord]) -> bool:
        if not self.is_configured():
            logger.warning(f"[{self.name}] Not configured, skipping")
            return False

        if not records:
            return True

        try:
            # Build email
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Court Records Alert: {len(records)} new filing(s)"
            msg["From"] = SMTP_USER
            msg["To"] = NOTIFY_EMAIL

            # Plain text version
            text_body = self._format_text(records)
            msg.attach(MIMEText(text_body, "plain"))

            # HTML version
            html_body = self._format_html(records)
            msg.attach(MIMEText(html_body, "html"))

            # Send
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, NOTIFY_EMAIL, msg.as_string())

            logger.info(f"[{self.name}] Sent email with {len(records)} records")
            return True

        except Exception as e:
            logger.error(f"[{self.name}] Failed to send email: {e}")
            return False

    def _format_text(self, records: list[CourtRecord]) -> str:
        """Format records as plain text."""
        lines = [
            f"Found {len(records)} new court record(s):",
            "",
            "=" * 50,
        ]

        for record in records:
            lines.append("")
            lines.append(self.format_record(record))
            lines.append("")
            lines.append("-" * 50)

        return "\n".join(lines)

    def _format_html(self, records: list[CourtRecord]) -> str:
        """Format records as HTML."""
        html = [
            "<html><body>",
            f"<h2>Found {len(records)} new court record(s)</h2>",
        ]

        for record in records:
            html.append("<div style='margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px;'>")
            html.append(f"<h3 style='margin-top: 0;'>{record.case_title}</h3>")
            html.append(f"<p><strong>Case #:</strong> {record.case_number}</p>")
            html.append(f"<p><strong>Court:</strong> {record.court}</p>")

            if record.filing_date:
                html.append(f"<p><strong>Filed:</strong> {record.filing_date}</p>")
            if record.case_type:
                html.append(f"<p><strong>Type:</strong> {record.case_type}</p>")

            html.append(f"<p><strong>Search term:</strong> {record.search_term}</p>")
            html.append(f"<p><a href='{record.url}'>View Record</a></p>")
            html.append("</div>")

        html.append("</body></html>")
        return "\n".join(html)
