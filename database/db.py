import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def _resolve_db_path(url: str) -> Path:
    """Convert a SQLite URL or plain path string to a filesystem Path.

    Accepts:
      sqlite:///./impact_engine.db
      sqlite:///impact_engine.db
      plain path strings (passed through as-is)

    Raises ValueError for non-SQLite or malformed URLs.
    """
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///"):])
    if url.startswith("sqlite://"):
        raise ValueError(
            f"Unsupported SQLite URL '{url}'. Use three slashes: sqlite:///./path.db"
        )
    if "://" in url:
        raise ValueError(
            f"Non-SQLite URLs are not supported by this engine. Got: '{url}'"
        )
    return Path(url)


DB_PATH = _resolve_db_path(settings.database_url)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                lead_id         TEXT PRIMARY KEY,
                decision        TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                outcome         TEXT NOT NULL,
                lead_value      REAL NOT NULL,
                customer_type   TEXT,
                value_tier      TEXT,
                source          TEXT,
                timestamp       TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        logger.info("Database initialised — leads table ready")
    finally:
        conn.close()


def insert_lead(lead: dict) -> None:
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO leads
                (lead_id, decision, confidence_score, outcome, lead_value,
                 customer_type, value_tier, source, timestamp)
            VALUES
                (:lead_id, :decision, :confidence_score, :outcome, :lead_value,
                 :customer_type, :value_tier, :source, :timestamp)
        """, lead)
        conn.commit()
    finally:
        conn.close()


def get_all_leads() -> List[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM leads ORDER BY timestamp ASC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_lead_by_id(lead_id: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM leads WHERE lead_id = ?", (lead_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_lead_count() -> int:
    conn = get_connection()
    try:
        result = conn.execute("SELECT COUNT(*) FROM leads").fetchone()
        return result[0]
    finally:
        conn.close()
