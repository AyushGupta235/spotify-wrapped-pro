import spotipy
from spotipy.oauth2 import SpotifyOAuth

from wrapped.config import CACHE_PATH, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPES


def get_client() -> spotipy.Spotify:
    auth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=" ".join(SCOPES),
        cache_path=str(CACHE_PATH),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth)
