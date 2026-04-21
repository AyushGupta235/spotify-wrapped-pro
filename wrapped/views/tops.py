import altair as alt
import streamlit as st

from wrapped.queries import top_albums, top_artists, top_tracks


def render(conn, period: str) -> None:
    artists_df = top_artists(conn, period)
    tracks_df = top_tracks(conn, period)
    albums_df = top_albums(conn, period)

    if artists_df.empty and tracks_df.empty:
        st.info("No play data yet for this period. Try refreshing or choose a wider time window.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Artists")
        if not artists_df.empty:
            chart = (
                alt.Chart(artists_df.head(10))
                .mark_bar()
                .encode(
                    x=alt.X("play_count:Q", title="Plays"),
                    y=alt.Y("name:N", sort="-x", title=""),
                    tooltip=["name", "play_count", "popularity"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(
                artists_df[["name", "play_count", "popularity"]].rename(
                    columns={"name": "Artist", "play_count": "Plays", "popularity": "Spotify Popularity"}
                ),
                hide_index=True,
                use_container_width=True,
            )

    with col2:
        st.subheader("Top Tracks")
        if not tracks_df.empty:
            chart = (
                alt.Chart(tracks_df.head(10))
                .mark_bar()
                .encode(
                    x=alt.X("play_count:Q", title="Plays"),
                    y=alt.Y("name:N", sort="-x", title=""),
                    tooltip=["name", "artist_name", "play_count"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(
                tracks_df[["name", "artist_name", "play_count"]].rename(
                    columns={"name": "Track", "artist_name": "Artist", "play_count": "Plays"}
                ),
                hide_index=True,
                use_container_width=True,
            )

    st.subheader("Top Albums")
    if not albums_df.empty:
        chart = (
            alt.Chart(albums_df.head(10))
            .mark_bar()
            .encode(
                x=alt.X("play_count:Q", title="Plays"),
                y=alt.Y("album_name:N", sort="-x", title=""),
                color=alt.Color("artist_name:N", legend=None),
                tooltip=["album_name", "artist_name", "play_count"],
            )
            .properties(height=280)
        )
        st.altair_chart(chart, use_container_width=True)
