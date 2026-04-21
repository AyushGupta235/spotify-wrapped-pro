"""Pure stat functions on DataFrames. No Spotify API calls, no DB calls."""
from typing import Optional

import pandas as pd


def obscurity_score(df: pd.DataFrame) -> Optional[float]:
    """Average artist popularity (0–100). Lower = more obscure."""
    col = "artist_popularity"
    if df.empty or col not in df.columns or df[col].isna().all():
        return None
    return round(float(df[col].mean()), 1)


def artist_diversity(df: pd.DataFrame) -> Optional[float]:
    """Unique artists / total plays in this period. Higher = more varied listening."""
    if df.empty or "artist_name" not in df.columns:
        return None
    return round(df["artist_name"].nunique() / len(df), 3)


def listening_sessions(df: pd.DataFrame, gap_minutes: int = 30) -> pd.DataFrame:
    """Cluster plays into sessions separated by silence of gap_minutes."""
    if df.empty or "played_at_ms" not in df.columns:
        return pd.DataFrame()
    d = df.sort_values("played_at_ms").copy()
    d["gap"] = d["played_at_ms"].diff().fillna(0)
    d["session_id"] = (d["gap"] > gap_minutes * 60 * 1000).cumsum()
    sessions = d.groupby("session_id").agg(
        start=("played_at_ms", "min"),
        end=("played_at_ms", "max"),
        play_count=("track_id", "count"),
    )
    sessions["duration_min"] = ((sessions["end"] - sessions["start"]) / 60_000).round(1)
    sessions["start_dt"] = pd.to_datetime(sessions["start"], unit="ms", utc=True)
    return sessions.sort_values("duration_min", ascending=False).reset_index(drop=True)


def longest_session(df: pd.DataFrame) -> Optional[dict]:
    sessions = listening_sessions(df)
    if sessions.empty:
        return None
    top = sessions.iloc[0]
    return {
        "date": top["start_dt"].strftime("%Y-%m-%d"),
        "duration_min": float(top["duration_min"]),
        "plays": int(top["play_count"]),
    }


def most_repeated_track_in_day(df: pd.DataFrame) -> Optional[dict]:
    if df.empty or "played_at" not in df.columns:
        return None
    d = df.copy()
    d["date"] = d["played_at"].dt.date
    counts = (
        d.groupby(["date", "track_id", "track_name"])
        .size()
        .reset_index(name="count")
    )
    if counts.empty:
        return None
    top = counts.loc[counts["count"].idxmax()]
    return {"date": str(top["date"]), "track": top["track_name"], "count": int(top["count"])}


def oldest_release(df: pd.DataFrame) -> Optional[dict]:
    if df.empty or "release_date" not in df.columns:
        return None
    d = df.dropna(subset=["release_date", "track_name"]).copy()
    if d.empty:
        return None
    idx = d["release_date"].idxmin()
    row = d.loc[idx]
    return {
        "track": row["track_name"],
        "release_date": row["release_date"],
        "artist": row.get("artist_name", ""),
    }


def decade_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "release_date" not in df.columns:
        return pd.DataFrame()
    d = df.dropna(subset=["release_date"]).copy()
    d["year"] = pd.to_numeric(d["release_date"].str[:4], errors="coerce")
    d = d.dropna(subset=["year"])
    d["decade"] = (d["year"] // 10 * 10).astype(int).astype(str) + "s"
    return (
        d.groupby("decade")
        .size()
        .reset_index(name="play_count")
        .sort_values("decade")
    )


def guilty_pleasure(df: pd.DataFrame) -> Optional[dict]:
    """Track with highest plays × lowest artist popularity — the hidden obsession."""
    if df.empty or "artist_popularity" not in df.columns:
        return None
    counts = (
        df.groupby(["track_id", "track_name", "artist_name", "artist_popularity"])
        .size()
        .reset_index(name="plays")
    )
    counts = counts.dropna(subset=["artist_popularity"])
    if counts.empty:
        return None
    counts["score"] = counts["plays"] * (100 - counts["artist_popularity"])
    top = counts.loc[counts["score"].idxmax()]
    return {
        "track": top["track_name"],
        "artist": top["artist_name"],
        "plays": int(top["plays"]),
        "artist_popularity": int(top["artist_popularity"]),
    }


def time_of_day_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Hour × weekday play counts for a listener heatmap."""
    if df.empty or "played_at" not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d["hour"] = d["played_at"].dt.hour
    d["weekday"] = d["played_at"].dt.day_name()
    return d.groupby(["hour", "weekday"]).size().reset_index(name="plays")


def discovery_rate_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly % of plays from artists first encountered that month."""
    if df.empty or "artist_name" not in df.columns or "played_at" not in df.columns:
        return pd.DataFrame()
    d = df.dropna(subset=["artist_name"]).copy()
    d["month"] = d["played_at"].dt.to_period("M").astype(str)
    first_seen = d.groupby("artist_name")["played_at"].min().rename("first_seen")
    d = d.join(first_seen, on="artist_name")
    d["first_seen_month"] = d["first_seen"].dt.to_period("M").astype(str)
    d["is_new"] = d["month"] == d["first_seen_month"]
    monthly = (
        d.groupby("month")
        .agg(total=("track_id", "count"), new=("is_new", "sum"))
        .reset_index()
    )
    monthly["discovery_rate"] = (monthly["new"] / monthly["total"] * 100).round(1)
    return monthly
