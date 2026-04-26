"""Import Extended Streaming History JSON files from Spotify's data export.

The extended history is the canonical, richest data source. Every field from
Spotify's export is stored verbatim so no information is lost. Fields that the
recently-played API can never provide (ms_played, reason_start/end, shuffle,
skipped, offline, incognito_mode, platform, conn_country) are all populated here.

Spotify extended history JSON field reference:
  ts                                 — ISO 8601 UTC timestamp (stream end)
  platform                           — device/OS string
  ms_played                          — milliseconds of audio played
  conn_country                       — ISO 3166-1 alpha-2
  master_metadata_track_name         — track name (denormalised, for reference)
  master_metadata_album_artist_name  — artist name (denormalised)
  master_metadata_album_album_name   — album name (denormalised)
  spotify_track_uri                  — "spotify:track:<id>"
  reason_start                       — why playback started
  reason_end                         — why playback ended
  shuffle                            — boolean | null
  skipped                            — boolean | null
  offline                            — boolean | null
  offline_timestamp                  — epoch ms when cached offline | null
  incognito_mode                     — boolean | null

Podcast entries (spotify_episode_uri set, spotify_track_uri null) are skipped.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from wrapped.db import get_connection

logger = logging.getLogger(__name__)


def run(path: str) -> int:
    """
    Import Spotify extended streaming history files.

    path: directory containing Streaming_History_Audio_*.json files,
          or a path to a single such JSON file.

    Returns number of plays imported (new rows — duplicates silently skipped).
    """
    p = Path(path)
    if p.is_dir():
        files = sorted(p.glob("Streaming_History_Audio_*.json"))
        if not files:
            files = sorted(p.glob("*.json"))
    else:
        files = [p]

    if not files:
        logger.warning("No JSON files found at %s", path)
        return 0

    conn = get_connection()
    total = 0

    for f in files:
        logger.info("Importing %s", f.name)
        entries = json.loads(f.read_text(encoding="utf-8"))
        count = _import_entries(conn, entries)
        logger.info("  %d plays from %s", count, f.name)
        total += count

    logger.info("Total imported: %d plays", total)
    return total


def _import_entries(conn, entries: list[dict]) -> int:
    count = 0
    for entry in entries:
        track_uri = entry.get("spotify_track_uri") or ""
        if not track_uri.startswith("spotify:track:"):
            # Skip podcasts and local files
            continue

        ts = entry.get("ts")
        if not ts:
            continue

        track_id = track_uri.split(":")[-1]
        played_at_ms = _iso_to_ms(ts)

        conn.execute(
            """INSERT OR IGNORE INTO plays (
                played_at_ms,
                track_id,
                ms_played,
                reason_start,
                reason_end,
                shuffle,
                skipped,
                offline,
                incognito_mode,
                platform,
                conn_country,
                context_type,
                context_uri,
                source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'extended')""",
            (
                played_at_ms,
                track_id,
                entry.get("ms_played"),
                entry.get("reason_start"),
                entry.get("reason_end"),
                _bool_to_int(entry.get("shuffle")),
                _bool_to_int(entry.get("skipped")),
                _bool_to_int(entry.get("offline")),
                _bool_to_int(entry.get("incognito_mode")),
                entry.get("platform"),
                entry.get("conn_country"),
            ),
        )
        count += 1

    conn.commit()
    return count


def _iso_to_ms(ts: str) -> int:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _bool_to_int(value) -> int | None:
    """Convert True/False/None from JSON to 1/0/None for SQLite INTEGER."""
    if value is None:
        return None
    return 1 if value else 0
