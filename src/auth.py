"""Autenticación OAuth con Spotify"""
import spotipy
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth
from .config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPES, APP_DIR, DATA_DIR
import sys

def get_spotify_client() -> spotipy.Spotify:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError('Completa CLIENT_ID y CLIENT_SECRET en .env y reinicia la aplicación.')
    cache_path = DATA_DIR.parent / '.cache' if getattr(sys, 'frozen', False) else APP_DIR / '.cache'
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    auth_manager = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=CacheFileHandler(cache_path=str(cache_path)),
    )
    return spotipy.Spotify(auth_manager=auth_manager, requests_timeout=30, retries=0, status_retries=0)
