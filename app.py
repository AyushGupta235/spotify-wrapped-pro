"""Spotify Wrapped — Personal Dashboard.

Run with:  streamlit run app.py
"""
import sqlite3
import time

import streamlit as st

from wrapped.config import CLIENT_ID, CLIENT_SECRET, DB_PATH
from wrapped.queries import total_plays

st.set_page_config(
    page_title="Spotify Wrapped",
    page_icon="🎧",
    layout="wide",
)

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_resource
def _get_connection() -> sqlite3.Connection:
    from wrapped.db import get_connection
    return get_connection()


def _run_ingest() -> str:
    """Run full ingestion pipeline and return a status string."""
    from wrapped.ingest import enrich as enrich_mod
    from wrapped.ingest import recent as recent_mod
    from wrapped.ingest import snapshot as snapshot_mod

    new = recent_mod.run()
    enrich_mod.run()
    snapshot_mod.run()
    st.cache_data.clear()
    return f"Pulled {new} new plays."


def _credentials_configured() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET and CLIENT_ID != "your_client_id_here")


def _has_data(conn: sqlite3.Connection) -> bool:
    return total_plays(conn) > 0


# ── First-run wizard ──────────────────────────────────────────────────────────

def _show_setup_wizard() -> None:
    st.title("🎧 Spotify Wrapped — Setup")
    st.markdown(
        "Welcome! Let's get your personal dashboard running. "
        "Everything stays **100% local** — nothing leaves your machine."
    )

    st.header("Step 1 — Create a Spotify Developer App")
    st.markdown(
        """
1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and log in.
2. Click **Create app** — name it anything you like.
3. Add this exact **Redirect URI**: `http://127.0.0.1:8888/callback`
   > Use `127.0.0.1`, **not** `localhost` — Spotify rejects the latter.
4. Save. Copy your **Client ID** and **Client Secret**.
        """
    )

    st.header("Step 2 — Add credentials to `.env`")
    st.markdown(
        "Edit the `.env` file in the project root (created from `.env.example` by `make setup`):"
    )
    st.code(
        "SPOTIPY_CLIENT_ID=your_client_id_here\n"
        "SPOTIPY_CLIENT_SECRET=your_client_secret_here\n"
        "SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback",
        language="bash",
    )
    st.markdown("Then **restart this app** (`Ctrl+C` → `make run`).")

    if not _credentials_configured():
        st.warning("Credentials not detected in `.env` yet. Fill them in and restart.")
        st.stop()

    st.header("Step 3 — Authorise & pull your data")
    st.markdown(
        "Click the button below. Your browser will open a Spotify login page — "
        "approve it, then come back here."
    )

    if st.button("Authorise Spotify & pull my listening history", type="primary"):
        with st.spinner("Authorising and pulling data (this may take a moment)..."):
            try:
                msg = _run_ingest()
                st.success(f"Done! {msg} Reloading dashboard...")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                st.markdown(
                    "**Common fixes:**\n"
                    "- Double-check the redirect URI is exactly `http://127.0.0.1:8888/callback`\n"
                    "- Make sure Client ID and Secret are correct in `.env`\n"
                    "- Delete `data/.cache` and try again if you get an auth loop"
                )
    st.stop()


# ── Period picker ─────────────────────────────────────────────────────────────

_PERIOD_LABELS = {
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "90d": "Last 90 days",
    "1y": "Last year",
    "all": "All time",
}


def _sidebar(conn: sqlite3.Connection) -> str:
    with st.sidebar:
        st.title("🎧 Spotify Wrapped")

        st.subheader("Time period")
        period = st.radio(
            "period",
            list(_PERIOD_LABELS.keys()),
            format_func=lambda k: _PERIOD_LABELS[k],
            index=1,  # default: 30d
            label_visibility="collapsed",
            key="period",
        )

        st.divider()

        if st.button("Refresh now", use_container_width=True):
            with st.spinner("Pulling latest plays..."):
                try:
                    msg = _run_ingest()
                    st.success(msg)
                except Exception as e:
                    st.error(str(e))

        n = total_plays(conn)
        st.caption(f"{n:,} plays in local DB")

    return period


# ── Main dashboard ────────────────────────────────────────────────────────────

def main() -> None:
    conn = _get_connection()

    if not _credentials_configured() or not _has_data(conn):
        _show_setup_wizard()
        return

    period = _sidebar(conn)

    from wrapped.views import evolution, fun, profile, tops

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Top", "Taste Profile", "Evolution", "Fun Facts"]
    )

    with tab1:
        tops.render(conn, period)

    with tab2:
        profile.render(conn, period)

    with tab3:
        evolution.render(conn, period)

    with tab4:
        fun.render(conn, period)


main()
