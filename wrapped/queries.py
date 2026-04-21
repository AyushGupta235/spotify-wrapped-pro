"""All SELECTs powering the dashboard. Read SQLite only — no Spotify API calls."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd


def _since_ms(period: str) -> Optional[int]:
    now = datetime.now(timezone.utc)
    mapping = {
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }
    if period not in mapping:
        return None
    return int((now - mapping[period]).timestamp() * 1000)


def _where_clause(period: str, alias: str = "p") -> str:
    since = _since_ms(period)
    return f"AND {alias}.played_at_ms >= {since}" if since else ""


def top_artists(conn: sqlite3.Connection, period: str = "30d", limit: int = 20) -> pd.DataFrame:
    where = _where_clause(period)
    sql = f"""
        SELECT a.id, a.name, a.popularity, a.genres_json,
               COUNT(*) AS play_count
        FROM plays p
        JOIN track_artists ta ON p.track_id = ta.track_id AND ta.position = 0
        JOIN artists a ON ta.artist_id = a.id
        WHERE 1=1 {where}
        GROUP BY a.id
        ORDER BY play_count DESC
        LIMIT {limit}
    """
    df = pd.read_sql_query(sql, conn)
    if not df.empty:
        df["genres"] = df["genres_json"].apply(lambda x: json.loads(x) if x else [])
    return df


def top_tracks(conn: sqlite3.Connection, period: str = "30d", limit: int = 20) -> pd.DataFrame:
    where = _where_clause(period)
    sql = f"""
        SELECT t.id, t.name, t.popularity, t.duration_ms, t.release_date,
               al.name AS album_name,
               a.name  AS artist_name,
               COUNT(*) AS play_count
        FROM plays p
        JOIN tracks t       ON p.track_id = t.id
        JOIN albums al      ON t.album_id = al.id
        JOIN track_artists ta ON t.id = ta.track_id AND ta.position = 0
        JOIN artists a      ON ta.artist_id = a.id
        WHERE 1=1 {where}
        GROUP BY t.id
        ORDER BY play_count DESC
        LIMIT {limit}
    """
    return pd.read_sql_query(sql, conn)


def top_albums(conn: sqlite3.Connection, period: str = "30d", limit: int = 20) -> pd.DataFrame:
    where = _where_clause(period)
    sql = f"""
        SELECT al.id, al.name AS album_name, al.release_date,
               a.name AS artist_name,
               COUNT(*) AS play_count
        FROM plays p
        JOIN tracks t       ON p.track_id = t.id
        JOIN albums al      ON t.album_id = al.id
        JOIN track_artists ta ON t.id = ta.track_id AND ta.position = 0
        JOIN artists a      ON ta.artist_id = a.id
        WHERE 1=1 {where}
        GROUP BY al.id
        ORDER BY play_count DESC
        LIMIT {limit}
    """
    return pd.read_sql_query(sql, conn)


def genre_breakdown(conn: sqlite3.Connection, period: str = "30d", top_n: int = 20) -> pd.DataFrame:
    where = _where_clause(period)
    sql = f"""
        SELECT a.genres_json, COUNT(*) AS play_count
        FROM plays p
        JOIN track_artists ta ON p.track_id = ta.track_id AND ta.position = 0
        JOIN artists a        ON ta.artist_id = a.id
        WHERE a.genres_json IS NOT NULL {where}
        GROUP BY a.id
    """
    rows = pd.read_sql_query(sql, conn).to_dict("records")
    genre_counts: dict[str, int] = {}
    for row in rows:
        genres = json.loads(row["genres_json"]) if row["genres_json"] else []
        for g in genres:
            genre_counts[g] = genre_counts.get(g, 0) + row["play_count"]
    if not genre_counts:
        return pd.DataFrame(columns=["genre", "play_count"])
    df = pd.DataFrame(list(genre_counts.items()), columns=["genre", "play_count"])
    return df.sort_values("play_count", ascending=False).head(top_n).reset_index(drop=True)


def audio_features_avg(conn: sqlite3.Connection, period: str = "30d") -> Optional[dict]:
    where = _where_clause(period)
    sql = f"""
        SELECT AVG(af.danceability)     AS danceability,
               AVG(af.energy)           AS energy,
               AVG(af.valence)          AS valence,
               AVG(af.acousticness)     AS acousticness,
               AVG(af.instrumentalness) AS instrumentalness,
               AVG(af.tempo)            AS tempo
        FROM plays p
        JOIN audio_features af ON p.track_id = af.track_id
        WHERE 1=1 {where}
    """
    row = conn.execute(sql).fetchone()
    if row and row[0] is not None:
        return dict(row)
    return None


def plays_over_time(conn: sqlite3.Connection, period: str = "30d") -> pd.DataFrame:
    since = _since_ms(period)
    where = f"WHERE played_at_ms >= {since}" if since else ""
    sql = f"""
        SELECT DATE(played_at_ms / 1000, 'unixepoch') AS date,
               COUNT(*) AS play_count
        FROM plays
        {where}
        GROUP BY date
        ORDER BY date
    """
    return pd.read_sql_query(sql, conn)


def snapshot_history(
    conn: sqlite3.Connection,
    kind: str = "artist",
    time_range: str = "short_term",
    limit: int = 10,
) -> pd.DataFrame:
    sql = """
        SELECT ts.captured_at,
               ts.rank,
               ts.entity_id,
               COALESCE(a.name, t.name) AS name
        FROM top_snapshots ts
        LEFT JOIN artists a ON ts.kind = 'artist' AND ts.entity_id = a.id
        LEFT JOIN tracks  t ON ts.kind = 'track'  AND ts.entity_id = t.id
        WHERE ts.kind = ? AND ts.time_range = ? AND ts.rank <= ?
        ORDER BY ts.captured_at, ts.rank
    """
    df = pd.read_sql_query(sql, conn, params=(kind, time_range, limit))
    if not df.empty:
        df["captured_at"] = pd.to_datetime(df["captured_at"])
    return df


def plays_raw(conn: sqlite3.Connection, period: str = "all") -> pd.DataFrame:
    """Full play rows joined with track/artist metadata. Used by stats.py."""
    since = _since_ms(period)
    where = f"WHERE p.played_at_ms >= {since}" if since else ""
    sql = f"""
        SELECT p.played_at_ms,
               p.track_id,
               t.name          AS track_name,
               t.duration_ms,
               t.release_date,
               t.popularity    AS track_popularity,
               a.name          AS artist_name,
               a.popularity    AS artist_popularity,
               a.genres_json,
               al.name         AS album_name
        FROM plays p
        LEFT JOIN tracks      t  ON p.track_id   = t.id
        LEFT JOIN track_artists ta ON p.track_id = ta.track_id AND ta.position = 0
        LEFT JOIN artists     a  ON ta.artist_id = a.id
        LEFT JOIN albums      al ON t.album_id   = al.id
        {where}
        ORDER BY p.played_at_ms
    """
    df = pd.read_sql_query(sql, conn)
    if not df.empty:
        df["played_at"] = pd.to_datetime(df["played_at_ms"], unit="ms", utc=True)
    return df


def total_plays(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0]


def audio_features_available(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT value FROM ingest_state WHERE key = 'audio_features_available'"
    ).fetchone()
    if row and row["value"] == "false":
        return False
    count = conn.execute("SELECT COUNT(*) FROM audio_features").fetchone()[0]
    return count > 0
