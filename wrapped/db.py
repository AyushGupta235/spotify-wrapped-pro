import sqlite3
from pathlib import Path

from wrapped.config import DB_PATH

_SCHEMA = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _bootstrap(conn)
    return conn


def _bootstrap(conn: sqlite3.Connection) -> None:
    schema = _SCHEMA.read_text()
    conn.executescript(schema)
    conn.commit()
