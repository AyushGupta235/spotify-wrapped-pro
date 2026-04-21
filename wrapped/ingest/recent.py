"""Poll /me/player/recently-played and upsert into the plays table."""
import logging
from datetime import datetime, timezone

from wrapped.auth import get_client
from wrapped.db import get_connection

logger = logging.getLogger(__name__)


def run() -> int:
    """Pull recent plays. Returns number of new rows inserted."""
    sp = get_client()
    conn = get_connection()

    row = conn.execute(
        "SELECT value FROM ingest_state WHERE key = 'last_recent_cursor'"
    ).fetchone()
    after_ms = int(row["value"]) if row else None

    new_count = 0
    cursor = after_ms
    latest_ms = after_ms or 0

    while True:
        kwargs: dict = {"limit": 50}
        if cursor:
            kwargs["after"] = cursor

        result = sp.current_user_recently_played(**kwargs)
        items = result.get("items", [])
        if not items:
            break

        for item in items:
            played_at_ms = _iso_to_ms(item["played_at"])
            track_id = item["track"]["id"]
            if not track_id:
                continue
            context = item.get("context") or {}
            conn.execute(
                "INSERT OR IGNORE INTO plays(played_at_ms, track_id, context_type, context_uri)"
                " VALUES (?,?,?,?)",
                (played_at_ms, track_id, context.get("type"), context.get("uri")),
            )
            if played_at_ms > latest_ms:
                latest_ms = played_at_ms
            new_count += 1

        conn.commit()

        next_cursor = (result.get("cursors") or {}).get("after")
        if not next_cursor:
            break
        cursor = int(next_cursor)

    if latest_ms:
        conn.execute(
            "INSERT OR REPLACE INTO ingest_state(key, value) VALUES ('last_recent_cursor', ?)",
            (str(latest_ms),),
        )
        conn.commit()

    logger.info("Ingested %d new plays", new_count)
    return new_count


def _iso_to_ms(ts: str) -> int:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)
