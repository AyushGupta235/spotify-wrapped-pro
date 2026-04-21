"""Weekly snapshot of /me/top/{artists,tracks} for all 3 Spotify time ranges."""
import logging
from datetime import datetime, timedelta, timezone

from wrapped.auth import get_client
from wrapped.db import get_connection

logger = logging.getLogger(__name__)

TIME_RANGES = ["short_term", "medium_term", "long_term"]


def run(force: bool = False) -> bool:
    """Take a snapshot. Returns True if a snapshot was actually written."""
    conn = get_connection()

    if not force:
        row = conn.execute(
            "SELECT value FROM ingest_state WHERE key = 'last_snapshot_at'"
        ).fetchone()
        if row:
            last = datetime.fromisoformat(row["value"])
            if datetime.now(timezone.utc) - last < timedelta(days=7):
                logger.info("Snapshot taken recently — skipping (pass force=True to override)")
                return False

    sp = get_client()
    captured_at = datetime.now(timezone.utc).isoformat()

    for kind in ("artists", "tracks"):
        for time_range in TIME_RANGES:
            if kind == "artists":
                result = sp.current_user_top_artists(limit=50, time_range=time_range)
            else:
                result = sp.current_user_top_tracks(limit=50, time_range=time_range)

            items = result.get("items", [])
            for rank, item in enumerate(items, start=1):
                conn.execute(
                    "INSERT OR REPLACE INTO top_snapshots"
                    "(captured_at, kind, time_range, rank, entity_id) VALUES (?,?,?,?,?)",
                    (captured_at, kind[:-1], time_range, rank, item["id"]),
                    # kind[:-1]: 'artists'→'artist', 'tracks'→'track'
                )

    conn.execute(
        "INSERT OR REPLACE INTO ingest_state(key, value) VALUES ('last_snapshot_at', ?)",
        (captured_at,),
    )
    conn.commit()
    logger.info("Snapshot taken at %s", captured_at)
    return True
