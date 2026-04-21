CREATE TABLE IF NOT EXISTS plays (
    played_at_ms   INTEGER PRIMARY KEY,
    track_id       TEXT NOT NULL,
    context_type   TEXT,
    context_uri    TEXT
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

CREATE TABLE IF NOT EXISTS top_snapshots (
    captured_at    TEXT NOT NULL,
    kind           TEXT NOT NULL,
    time_range     TEXT NOT NULL,
    rank           INTEGER NOT NULL,
    entity_id      TEXT NOT NULL,
    PRIMARY KEY (captured_at, kind, time_range, rank)
);

CREATE TABLE IF NOT EXISTS ingest_state (
    key            TEXT PRIMARY KEY,
    value          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plays_played_at  ON plays(played_at_ms);
CREATE INDEX IF NOT EXISTS idx_plays_track      ON plays(track_id);
CREATE INDEX IF NOT EXISTS idx_top_snapshots    ON top_snapshots(kind, time_range, captured_at);
CREATE INDEX IF NOT EXISTS idx_track_artists_a  ON track_artists(artist_id);
