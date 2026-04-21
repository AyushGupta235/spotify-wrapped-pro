import altair as alt
import streamlit as st

from wrapped.queries import plays_raw, total_plays
from wrapped.stats import (
    artist_diversity,
    decade_distribution,
    guilty_pleasure,
    longest_session,
    most_repeated_track_in_day,
    obscurity_score,
    oldest_release,
    time_of_day_heatmap,
)

_DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def render(conn, period: str) -> None:
    raw_df = plays_raw(conn, period)
    n_total = total_plays(conn)

    if raw_df.empty:
        st.info("No play data yet. Hit **Refresh now** in the sidebar to pull your history.")
        return

    # ── Key metrics row ──────────────────────────────────────────────
    obscurity = obscurity_score(raw_df)
    diversity = artist_diversity(raw_df)
    session = longest_session(raw_df)
    repeated = most_repeated_track_in_day(raw_df)

    cols = st.columns(4)
    cols[0].metric(
        "Total Plays (all time)",
        f"{n_total:,}",
        help="All plays ever stored in the local DB",
    )
    cols[1].metric(
        "Obscurity Score",
        f"{obscurity}/100" if obscurity is not None else "—",
        help="Avg artist popularity in this period. 0 = maximally obscure, 100 = mainstream.",
    )
    cols[2].metric(
        "Artist Diversity",
        f"{diversity:.1%}" if diversity is not None else "—",
        help="Unique artists ÷ total plays. Higher = more varied listening.",
    )
    if session:
        cols[3].metric(
            "Longest Session",
            f"{session['duration_min']:.0f} min",
            help=f"{session['plays']} tracks on {session['date']}",
        )
    else:
        cols[3].metric("Longest Session", "—")

    st.divider()

    # ── Two-column nuggets ───────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Quick Facts")

        if repeated:
            st.markdown(
                f"**Most replayed in a day:** _{repeated['track']}_ "
                f"— {repeated['count']}× on {repeated['date']}"
            )

        oldest = oldest_release(raw_df)
        if oldest:
            year = oldest["release_date"][:4]
            st.markdown(
                f"**Oldest track played:** _{oldest['track']}_ "
                f"by {oldest['artist']} ({year})"
            )

        guilty = guilty_pleasure(raw_df)
        if guilty:
            st.markdown(
                f"**Guilty pleasure:** _{guilty['track']}_ by {guilty['artist']} "
                f"— played {guilty['plays']}× "
                f"(artist popularity: {guilty['artist_popularity']}/100)"
            )

    with col_b:
        st.subheader("By Decade")
        decades_df = decade_distribution(raw_df)
        if not decades_df.empty:
            chart = (
                alt.Chart(decades_df)
                .mark_bar()
                .encode(
                    x=alt.X("decade:O", title="Decade"),
                    y=alt.Y("play_count:Q", title="Plays"),
                    color=alt.Color("play_count:Q", scale=alt.Scale(scheme="oranges"), legend=None),
                    tooltip=["decade", "play_count"],
                )
                .properties(height=220)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Need release-date metadata — run `ingest enrich` first.")

    # ── Listening heatmap ────────────────────────────────────────────
    st.subheader("When Do You Listen?")
    heatmap_df = time_of_day_heatmap(raw_df)
    if not heatmap_df.empty:
        chart = (
            alt.Chart(heatmap_df)
            .mark_rect()
            .encode(
                x=alt.X("weekday:O", sort=_DAYS_ORDER, title=""),
                y=alt.Y("hour:O", title="Hour of day (local)"),
                color=alt.Color(
                    "plays:Q",
                    scale=alt.Scale(scheme="blues"),
                    title="Plays",
                ),
                tooltip=["weekday", "hour", "plays"],
            )
            .properties(height=380)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Not enough data for a heatmap yet.")
