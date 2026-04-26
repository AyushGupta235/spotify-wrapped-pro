import sqlite3
from pathlib import Path

from wrapped.config import DB_PATH

_SCHEMA = Path(__file__).parent / "schema.sql"

# Columns added after the initial release that need to be migrated onto
# existing databases. Each tuple is (table, column, definition).
_MIGRATIONS = [
    ("plays", "ms_played",       "INTEGER"),
    ("plays", "reason_start",    "TEXT"),
    ("plays", "reason_end",      "TEXT"),
    ("plays", "shuffle",         "INTEGER"),
    ("plays", "skipped",         "INTEGER"),
    ("plays", "offline",         "INTEGER"),
    ("plays", "incognito_mode",  "INTEGER"),
    ("plays", "platform",        "TEXT"),
    ("plays", "conn_country",    "TEXT"),
    ("plays", "source",          "TEXT NOT NULL DEFAULT 'recent'"),
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _bootstrap(conn)
    _migrate(conn)
    return conn


def _bootstrap(conn: sqlite3.Connection) -> None:
    schema = _SCHEMA.read_text()
    conn.executescript(schema)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial schema creation (idempotent)."""
    existing: dict[str, set[str]] = {}
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        table = row["name"]
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        existing[table] = cols

    for table, column, definition in _MIGRATIONS:
        if table in existing and column not in existing[table]:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    conn.commit()
