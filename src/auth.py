"""Autenticación OAuth con Spotify"""
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from .config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPES

def get_spotify_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
    )
    return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=30, retries=0, status_retries=0)
