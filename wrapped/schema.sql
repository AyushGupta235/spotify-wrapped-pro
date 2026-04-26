CREATE TABLE IF NOT EXISTS plays (
    -- Primary key: Unix timestamp in ms of when the stream ended (consistent
    -- across both the recently-played API and the extended history export).
    played_at_ms      INTEGER PRIMARY KEY,

    -- Track identity
    track_id          TEXT NOT NULL,

    -- How long the track was actually played (ms).
    -- NULL when sourced from recently-played (API doesn't expose this).
    -- Populated from extended history export.
    ms_played         INTEGER,

    -- Why playback started / ended.
    -- Values: "trackdone", "fwdbtn", "backbtn", "clickrow", "playbtn",
    --         "appload", "remote", "endplay", "logout", "popup", etc.
    -- NULL when sourced from recently-played.
    reason_start      TEXT,
    reason_end        TEXT,

    -- Playback context
    shuffle           INTEGER,   -- BOOLEAN: 1/0/NULL
    skipped           INTEGER,   -- BOOLEAN: 1/0/NULL (often NULL even in extended history)
    offline           INTEGER,   -- BOOLEAN: 1/0/NULL
    incognito_mode    INTEGER,   -- BOOLEAN: 1/0/NULL

    -- Device / location
    platform          TEXT,      -- e.g. "Android OS 13", "Windows 10 (10.0.19043)"
    conn_country      TEXT,      -- ISO 3166-1 alpha-2, e.g. "US"

    -- Spotify playback context (populated from recently-played, NULL from extended)
    context_type      TEXT,      -- "playlist", "album", "artist", etc.
    context_uri       TEXT,      -- e.g. "spotify:playlist:..."

    -- Provenance: which pipeline wrote this row
    source            TEXT NOT NULL DEFAULT 'recent'  -- 'recent' | 'extended'
);

CREATE TABLE IF NOT EXISTS tracks (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    album_id       TEXT,
    duration_ms    INTEGER,
    popularity     INTEGER,
    explicit       INTEGER,
    release_date   TEXT
);

CREATE TABLE IF NOT EXISTS artists (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    popularity     INTEGER,
    followers      INTEGER,
    genres_json    TEXT
);

CREATE TABLE IF NOT EXISTS albums (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    release_date   TEXT,
    image_url      TEXT
);

CREATE TABLE IF NOT EXISTS track_artists (
    track_id       TEXT NOT NULL,
    artist_id      TEXT NOT NULL,
    position       INTEGER NOT NULL,
    PRIMARY KEY (track_id, artist_id)
);

CREATE TABLE IF NOT EXISTS audio_features (
    track_id         TEXT PRIMARY KEY,
    danceability     REAL,
    energy           REAL,
    valence          REAL,
    tempo            REAL,
    acousticness     REAL,
    instrumentalness REAL,
    speechiness      REAL,
    liveness         REAL,
    loudness         REAL
);

-- Weekly snapshots of /me/top/{artists,tracks} for rank-over-time charts.
CREATE TABLE IF NOT EXISTS top_snapshots (
    captured_at    TEXT NOT NULL,
    kind           TEXT NOT NULL,       -- 'artist' | 'track'
    time_range     TEXT NOT NULL,       -- 'short_term' | 'medium_term' | 'long_term'
    rank           INTEGER NOT NULL,
    entity_id      TEXT NOT NULL,
    PRIMARY KEY (captured_at, kind, time_range, rank)
);

-- Key-value store for pipeline state (cursors, timestamps, feature flags).
CREATE TABLE IF NOT EXISTS ingest_state (
    key            TEXT PRIMARY KEY,
    value          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plays_played_at  ON plays(played_at_ms);
CREATE INDEX IF NOT EXISTS idx_plays_track      ON plays(track_id);
CREATE INDEX IF NOT EXISTS idx_plays_source     ON plays(source);
CREATE INDEX IF NOT EXISTS idx_top_snapshots    ON top_snapshots(kind, time_range, captured_at);
CREATE INDEX IF NOT EXISTS idx_track_artists_a  ON track_artists(artist_id);
