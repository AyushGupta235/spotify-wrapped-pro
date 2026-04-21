"""Import Extended Streaming History JSON files from Spotify's data export."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from wrapped.db import get_connection

logger = logging.getLogger(__name__)


def run(path: str) -> int:
    """
    Import Spotify extended history files into the plays table.

    path: path to a directory containing Streaming_History_Audio_*.json files,
          or a path to a single such JSON file.

    Returns the number of plays imported.
    """
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("Streaming_History_Audio_*.json"))
        if not files:
            # Fall back to any JSON in the directory
            files = sorted(p.glob("*.json"))
    else:
        files = [p]

    if not files:
        logger.warning("No JSON files found at %s", path)
        return 0

    conn = get_connection()
    count = 0

    for f in files:
        logger.info("Importing %s", f.name)
        data = json.loads(f.read_text(encoding="utf-8"))
        for entry in data:
            ts = entry.get("ts")
            track_uri = entry.get("spotify_track_uri", "")
            if not ts or not track_uri.startswith("spotify:track:"):
                continue
            track_id = track_uri.split(":")[-1]
            played_at_ms = _iso_to_ms(ts)
            conn.execute(
                "INSERT OR IGNORE INTO plays(played_at_ms, track_id, context_type, context_uri)"
                " VALUES (?,?,?,?)",
                (played_at_ms, track_id, None, None),
            )
            count += 1
        conn.commit()
        logger.info("  → %d entries processed", count)

    logger.info("Imported %d plays from extended history", count)
    return count


def _iso_to_ms(ts: str) -> int:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)
