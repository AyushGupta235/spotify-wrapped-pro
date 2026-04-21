import altair as alt
import pandas as pd
import streamlit as st

from wrapped.queries import audio_features_avg, audio_features_available, genre_breakdown


def render(conn, period: str) -> None:
    genres_df = genre_breakdown(conn, period)

    if not genres_df.empty:
        st.subheader("Genre Breakdown")
        chart = (
            alt.Chart(genres_df.head(15))
            .mark_bar()
            .encode(
                x=alt.X("play_count:Q", title="Plays"),
                y=alt.Y("genre:N", sort="-x", title=""),
                color=alt.Color("play_count:Q", scale=alt.Scale(scheme="tealblues"), legend=None),
                tooltip=["genre", "play_count"],
            )
            .properties(height=420)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Genre data not available yet. Refresh to pull artist metadata.")

    st.subheader("Audio Feature Profile")

    if not audio_features_available(conn):
        st.info(
            "**Audio features unavailable** — Spotify deprecated this endpoint for apps created "
            "after Nov 2024. Genre breakdown above is still a solid taste signal."
        )
        return

    avg = audio_features_avg(conn, period)
    if not avg:
        st.info("Not enough audio feature data yet for this period.")
        return

    features = {
        "Danceability": avg["danceability"],
        "Energy": avg["energy"],
        "Valence (Happiness)": avg["valence"],
        "Acousticness": avg["acousticness"],
        "Instrumentalness": avg["instrumentalness"],
    }
    df = pd.DataFrame(list(features.items()), columns=["feature", "value"])

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("value:Q", scale=alt.Scale(domain=[0, 1]), title="Score (0–1)"),
            y=alt.Y("feature:N", sort="-x", title=""),
            color=alt.Color(
                "value:Q",
                scale=alt.Scale(scheme="viridis"),
                legend=None,
            ),
            tooltip=["feature", alt.Tooltip("value:Q", format=".2f")],
        )
        .properties(height=220)
    )
    st.altair_chart(chart, use_container_width=True)

    cols = st.columns(len(features))
    for col, (feat, val) in zip(cols, features.items()):
        col.metric(feat.split("(")[0].strip(), f"{val:.0%}")

    if avg.get("tempo"):
        st.metric("Avg Tempo", f"{avg['tempo']:.0f} BPM")
