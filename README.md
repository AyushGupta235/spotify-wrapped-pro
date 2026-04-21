# spotify-wrapped-pro

**Year-round personal Spotify Wrapped.** A privacy-first dashboard that runs entirely locally using your own Spotify developer app. No third-party services, no data leaving your machine.

## Why This Exists

Spotify Wrapped is great, but it only drops once a year. If you're a music person who cares about how your taste evolves, you want to check in more often — see what's trending in your library right now, what genres dominate, how your listening habits change across months.

This is a **personal dashboard** that lets you:
- Track your top artists, tracks, albums across custom time windows (7d, 30d, 90d, 1y, all-time)
- Explore your taste profile: genre breakdown + audio features (danceability, energy, valence, etc.)
- Watch your listening evolve: rank trends, discovery rate, monthly activity
- Spot patterns: obscurity score, listening heatmap (when/what day do you listen?), longest sessions, guilty pleasures

All data stays on your machine. All runs locally. Costs nothing.

## Quick Start

### 1. Create a Spotify Developer App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create app** — name it anything you like.
3. Set **Redirect URI** to exactly: `http://127.0.0.1:8888/callback`
   > ⚠️ Use `127.0.0.1`, not `localhost` — Spotify rejects the latter.
4. Save. Copy your **Client ID** and **Client Secret**.

### 2. Install & Configure

```bash
make setup          # creates venv, installs deps, creates .env
```

Edit `.env` and paste your credentials:

```
SPOTIPY_CLIENT_ID=abc123...
SPOTIPY_CLIENT_SECRET=xyz789...
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

### 3. Run

```bash
make run            # opens dashboard at http://localhost:8501
```

The first-run wizard walks you through Spotify OAuth and pulls your initial data automatically.

## What You Get

### Dashboard Tabs

| Tab | Shows |
|---|---|
| **Top** | Top artists, tracks, albums with play counts |
| **Taste Profile** | Genre breakdown + audio feature radar (danceability, energy, valence, tempo, acousticness) |
| **Evolution** | Rank-over-time trends, discovery rate, daily/weekly activity |
| **Fun Facts** | Obscurity score, listening heatmap, longest session, guilty pleasure, decade distribution, release dates |

**Period picker** (sidebar): Last 7d / 30d / 90d / 1y / All-time — computed from local history.

### CLI Commands

```bash
make whoami                          # verify auth
make ingest                          # pull recent plays + enrich + snapshot
python -m scripts.ingest recent      # just pull recent plays
python -m scripts.ingest enrich      # fetch metadata for new tracks
python -m scripts.ingest snapshot    # take a weekly top-items snapshot
python -m scripts.ingest import-extended /path/to/spotify/data  # optional: backfill extended history
```

## Architecture

```
spotify-wrapped-pro/
├── app.py                   # Streamlit entry, first-run wizard, 4 tabs
├── wrapped/
│   ├── auth.py              # Spotipy OAuth client
│   ├── db.py                # SQLite connection + schema bootstrap
│   ├── config.py            # env loading, paths
│   ├── ingest/              # data collection pipeline
│   │   ├── recent.py        # /me/player/recently-played polling
│   │   ├── snapshot.py      # /me/top/{artists,tracks} weekly snapshot
│   │   ├── enrich.py        # metadata + audio features (graceful 403 fallback)
│   │   └── extended.py      # Streaming_History_Audio_*.json importer
│   ├── queries.py           # all SQL queries powering the dashboard
│   ├── stats.py             # pure stat functions (obscurity, diversity, sessions, etc.)
│   └── views/               # one module per tab
│       ├── tops.py          # top artists/tracks/albums
│       ├── profile.py       # genre + audio features
│       ├── evolution.py     # trends + snapshots
│       └── fun.py           # fun facts + heatmap
├── scripts/
│   └── ingest.py            # typer CLI for data collection
├── data/                    # local SQLite DB + auth cache (gitignored)
└── pyproject.toml           # dependencies
```

**Storage:** SQLite (`data/history.db`) with 8 tables:
- `plays`: play records from recently-played (played_at_ms, track_id, context)
- `tracks`, `artists`, `albums`: metadata
- `audio_features`: danceability, energy, valence, tempo, etc.
- `top_snapshots`: weekly snapshots of your top 50 artists/tracks (3 time ranges)
- `ingest_state`: cursor tracking, last snapshot timestamp

**Ingestion:**
- `recent`: polls `/me/player/recently-played` (50 items max, paginated via cursors). Idempotent — safe to run hourly.
- `enrich`: for any new track_id, fetches `/tracks`, `/artists`, `/audio-features` (batched 50 IDs per call).
- `snapshot`: captures `/me/top/{artists,tracks}` for short/medium/long-term ranges. Runs weekly by default.
- `import-extended`: optional — parse Spotify's extended history export (takes 2–4 weeks to request) for full backfill.

## Optional: Automatic Background Collection

By default, the dashboard collects on app launch and via "Refresh now" button. For continuous background polling, set up a launchd job:

```bash
cat > ~/Library/LaunchAgents/com.spotify-wrapped.ingest.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.spotify-wrapped.ingest</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/.venv/bin/python</string>
        <string>-m</string>
        <string>scripts.ingest</string>
        <string>all</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/spotify-wrapped-pro</string>
    <key>StartInterval</key>
    <integer>3600</integer>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.spotify-wrapped.ingest.plist
```

(Edit paths to match your setup.)

## ⚠️ Audio Features Caveat

Spotify deprecated the `/audio-features` endpoint for **new developer apps** created after Nov 27, 2024. If your app is newer, the audio feature radar won't work — but genre breakdown still provides a solid taste signal. The code gracefully falls back.

## Tech Stack

- **Frontend**: Streamlit (zero-config dashboards)
- **Backend**: Python + SQLite (all local)
- **Spotify API**: Spotipy
- **Charts**: Altair (lightweight, crisp)
- **Data**: Pandas (queries → DataFrames)

## Privacy & Security

✅ **All data stays on your machine.** No cloud upload, no tracking, no third-party APIs.

- Listen history lives in `data/history.db` (SQLite, local).
- Spotify OAuth tokens cached in `data/.cache` (local, gitignored).
- Credentials in `.env` (gitignored).
- Only calls to Spotify's own API (with your auth).

## Getting Help

- **Auth failing?** Check that redirect URI is exactly `http://127.0.0.1:8888/callback` in your Spotify app settings.
- **No data showing?** Run `make whoami` to verify auth, then `make ingest` to pull data.
- **Audio features missing?** Check the info box in the Taste Profile tab — might be a deprecated endpoint.

---

Built with ♫ for music lovers who want to understand their listening.
