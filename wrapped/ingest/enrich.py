"""Fetch track/artist metadata and audio features for unenriched plays."""
import json
import logging
import time

from wrapped.auth import get_client
from wrapped.db import get_connection

logger = logging.getLogger(__name__)
BATCH = 50


def run() -> None:
    conn = get_connection()
    sp = get_client()
    _enrich_tracks(conn, sp)
    _enrich_artists(conn, sp)
    _enrich_audio_features(conn, sp)


def _enrich_tracks(conn, sp) -> None:
    rows = conn.execute(
        "SELECT DISTINCT p.track_id FROM plays p"
        " LEFT JOIN tracks t ON p.track_id = t.id WHERE t.id IS NULL"
    ).fetchall()
    ids = [r["track_id"] for r in rows]
    if not ids:
        return
    logger.info("Enriching %d tracks", len(ids))

    for i in range(0, len(ids), BATCH):
        batch = ids[i : i + BATCH]
        result = sp.tracks(batch)
        for track in result["tracks"]:
            if not track:
                continue
            album = track.get("album", {})
            images = album.get("images") or [{}]
            conn.execute(
                "INSERT OR IGNORE INTO albums(id, name, release_date, image_url) VALUES (?,?,?,?)",
                (album.get("id"), album.get("name"), album.get("release_date"), images[0].get("url")),
            )
            conn.execute(
                "INSERT OR IGNORE INTO tracks"
                "(id, name, album_id, duration_ms, popularity, explicit, release_date)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    track["id"],
                    track["name"],
                    album.get("id"),
                    track.get("duration_ms"),
                    track.get("popularity"),
                    int(track.get("explicit", False)),
                    album.get("release_date"),
                ),
            )
            for pos, artist in enumerate(track.get("artists", [])):
                conn.execute(
                    "INSERT OR IGNORE INTO track_artists(track_id, artist_id, position) VALUES (?,?,?)",
                    (track["id"], artist["id"], pos),
                )
        conn.commit()
        if i + BATCH < len(ids):
            time.sleep(0.1)


def _enrich_artists(conn, sp) -> None:
    rows = conn.execute(
        "SELECT DISTINCT ta.artist_id FROM track_artists ta"
        " LEFT JOIN artists a ON ta.artist_id = a.id WHERE a.id IS NULL"
    ).fetchall()
    ids = [r["artist_id"] for r in rows]
    if not ids:
        return
    logger.info("Enriching %d artists", len(ids))

    for i in range(0, len(ids), BATCH):
        batch = ids[i : i + BATCH]
        result = sp.artists(batch)
        for artist in result["artists"]:
            if not artist:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO artists(id, name, popularity, followers, genres_json)"
                " VALUES (?,?,?,?,?)",
                (
                    artist["id"],
                    artist["name"],
                    artist.get("popularity"),
                    (artist.get("followers") or {}).get("total"),
                    json.dumps(artist.get("genres", [])),
                ),
            )
        conn.commit()
        if i + BATCH < len(ids):
            time.sleep(0.1)


def _enrich_audio_features(conn, sp) -> None:
    rows = conn.execute(
        "SELECT DISTINCT t.id FROM tracks t"
        " LEFT JOIN audio_features af ON t.id = af.track_id WHERE af.track_id IS NULL"
    ).fetchall()
    ids = [r["id"] for r in rows]
    if not ids:
        return
    logger.info("Fetching audio features for %d tracks", len(ids))

    try:
        for i in range(0, len(ids), BATCH):
            batch = ids[i : i + BATCH]
            features = sp.audio_features(batch)
            if not features:
                continue
            for af in features:
                if not af:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO audio_features"
                    "(track_id, danceability, energy, valence, tempo,"
                    " acousticness, instrumentalness, speechiness, liveness, loudness)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        af["id"],
                        af["danceability"],
                        af["energy"],
                        af["valence"],
                        af["tempo"],
                        af["acousticness"],
                        af["instrumentalness"],
                        af["speechiness"],
                        af["liveness"],
                        af["loudness"],
                    ),
                )
            conn.commit()
            if i + BATCH < len(ids):
                time.sleep(0.1)
        logger.info("Audio features enriched")
    except Exception as e:
        if "403" in str(e):
            logger.warning(
                "Audio features endpoint returned 403 — deprecated for apps created after Nov 2024. Skipping."
            )
            conn.execute(
                "INSERT OR REPLACE INTO ingest_state(key, value)"
                " VALUES ('audio_features_available', 'false')"
            )
            conn.commit()
        else:
            raise
