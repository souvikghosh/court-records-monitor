import aiosqlite
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CourtRecord:
    """Represents a court record entry."""
    id: Optional[int]
    court: str  # Source court system
    case_number: str
    case_title: str
    filing_date: Optional[str]
    case_type: Optional[str]
    parties: Optional[str]  # JSON string of parties involved
    url: str
    search_term: str  # Which search term found this
    first_seen: datetime
    last_seen: datetime
    notified: bool = False

    @property
    def unique_key(self) -> str:
        """Unique identifier for deduplication."""
        return f"{self.court}:{self.case_number}"


class Database:
    """Async SQLite database for tracking court records."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Open database connection and create tables."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                court TEXT NOT NULL,
                case_number TEXT NOT NULL,
                case_title TEXT NOT NULL,
                filing_date TEXT,
                case_type TEXT,
                parties TEXT,
                url TEXT NOT NULL,
                search_term TEXT NOT NULL,
                first_seen TIMESTAMP NOT NULL,
                last_seen TIMESTAMP NOT NULL,
                notified INTEGER DEFAULT 0,
                UNIQUE(court, case_number)
            )
        """)

        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_records_search_term
            ON records(search_term)
        """)

        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_records_court
            ON records(court)
        """)

        await self._connection.commit()

    async def record_exists(self, court: str, case_number: str) -> bool:
        """Check if a record already exists."""
        cursor = await self._connection.execute(
            "SELECT 1 FROM records WHERE court = ? AND case_number = ?",
            (court, case_number)
        )
        row = await cursor.fetchone()
        return row is not None

    async def add_record(self, record: CourtRecord) -> tuple[int, bool]:
        """
        Add or update a court record.

        Returns:
            Tuple of (record_id, is_new)
        """
        now = datetime.utcnow()

        # Check if exists
        cursor = await self._connection.execute(
            "SELECT id FROM records WHERE court = ? AND case_number = ?",
            (record.court, record.case_number)
        )
        existing = await cursor.fetchone()

        if existing:
            # Update last_seen
            await self._connection.execute(
                "UPDATE records SET last_seen = ? WHERE id = ?",
                (now, existing["id"])
            )
            await self._connection.commit()
            return existing["id"], False

        # Insert new record
        cursor = await self._connection.execute(
            """
            INSERT INTO records
            (court, case_number, case_title, filing_date, case_type, parties,
             url, search_term, first_seen, last_seen, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.court,
                record.case_number,
                record.case_title,
                record.filing_date,
                record.case_type,
                record.parties,
                record.url,
                record.search_term,
                now,
                now,
                0
            )
        )
        await self._connection.commit()
        return cursor.lastrowid, True

    async def mark_notified(self, record_id: int) -> None:
        """Mark a record as notified."""
        await self._connection.execute(
            "UPDATE records SET notified = 1 WHERE id = ?",
            (record_id,)
        )
        await self._connection.commit()

    async def get_unnotified_records(self) -> list[CourtRecord]:
        """Get all records that haven't been notified yet."""
        cursor = await self._connection.execute(
            "SELECT * FROM records WHERE notified = 0 ORDER BY first_seen DESC"
        )
        rows = await cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_records_by_search_term(self, search_term: str) -> list[CourtRecord]:
        """Get all records for a specific search term."""
        cursor = await self._connection.execute(
            "SELECT * FROM records WHERE search_term = ? ORDER BY first_seen DESC",
            (search_term,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_recent_records(self, limit: int = 50) -> list[CourtRecord]:
        """Get most recent records."""
        cursor = await self._connection.execute(
            "SELECT * FROM records ORDER BY first_seen DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_record(row) for row in rows]

    async def get_stats(self) -> dict:
        """Get database statistics."""
        cursor = await self._connection.execute(
            "SELECT COUNT(*) as total, SUM(notified) as notified FROM records"
        )
        row = await cursor.fetchone()

        cursor = await self._connection.execute(
            "SELECT court, COUNT(*) as count FROM records GROUP BY court"
        )
        by_court = {r["court"]: r["count"] for r in await cursor.fetchall()}

        return {
            "total_records": row["total"] or 0,
            "notified": row["notified"] or 0,
            "by_court": by_court
        }

    def _row_to_record(self, row: aiosqlite.Row) -> CourtRecord:
        """Convert database row to CourtRecord."""
        return CourtRecord(
            id=row["id"],
            court=row["court"],
            case_number=row["case_number"],
            case_title=row["case_title"],
            filing_date=row["filing_date"],
            case_type=row["case_type"],
            parties=row["parties"],
            url=row["url"],
            search_term=row["search_term"],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_seen=datetime.fromisoformat(row["last_seen"]),
            notified=bool(row["notified"])
        )
