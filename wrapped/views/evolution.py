import altair as alt
import streamlit as st

from wrapped.queries import plays_over_time, plays_raw, snapshot_history
from wrapped.stats import discovery_rate_by_month


def render(conn, period: str) -> None:
    # Daily activity chart
    daily_df = plays_over_time(conn, period)
    if not daily_df.empty:
        st.subheader("Listening Activity")
        chart = (
            alt.Chart(daily_df)
            .mark_area(opacity=0.75, color="#1DB954")
            .encode(
                x=alt.X("date:T", title="Date"),
                y=alt.Y("play_count:Q", title="Plays per day"),
                tooltip=["date:T", "play_count:Q"],
            )
            .properties(height=200)
        )
        st.altair_chart(chart, use_container_width=True)

    # Rank-over-time from snapshots
    st.subheader("Rank Over Time (Spotify Snapshots)")
    st.caption(
        "Snapshots are taken weekly. After your first week you'll see trends here. "
        "Run `python -m scripts.ingest snapshot --force` to capture one immediately."
    )

    col1, col2 = st.columns(2)
    with col1:
        time_range = st.selectbox(
            "Spotify time range",
            ["short_term", "medium_term", "long_term"],
            key="evo_range",
            format_func=lambda x: {
                "short_term": "Last ~4 weeks",
                "medium_term": "Last ~6 months",
                "long_term": "All time",
            }[x],
        )
    with col2:
        kind = st.selectbox("Show", ["artist", "track"], key="evo_kind")

    snap_df = snapshot_history(conn, kind=kind, time_range=time_range, limit=10)

    if snap_df.empty:
        st.info("No snapshots yet — come back after your first week, or force one via the CLI.")
    else:
        chart = (
            alt.Chart(snap_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("captured_at:T", title="Snapshot date"),
                y=alt.Y("rank:Q", scale=alt.Scale(reverse=True), title="Rank (1 = top)"),
                color=alt.Color("name:N", title="Artist" if kind == "artist" else "Track"),
                tooltip=["name", "rank", alt.Tooltip("captured_at:T", title="Date")],
            )
            .properties(height=350)
        )
        st.altair_chart(chart, use_container_width=True)

    # Monthly discovery rate
    st.subheader("Monthly Discovery Rate")
    st.caption("% of plays each month from artists you'd never played before.")
    raw_df = plays_raw(conn, period="all")
    disc_df = discovery_rate_by_month(raw_df)
    if not disc_df.empty and len(disc_df) >= 2:
        chart = (
            alt.Chart(disc_df)
            .mark_bar()
            .encode(
                x=alt.X("month:O", title="Month"),
                y=alt.Y("discovery_rate:Q", title="New-artist plays (%)"),
                tooltip=["month", "discovery_rate", "total", "new"],
            )
            .properties(height=250)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Need at least 2 months of data to show discovery rate trends.")
