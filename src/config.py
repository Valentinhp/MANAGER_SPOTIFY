"""
Carga variables de entorno y configura logging
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
DATA_DIR = (Path(os.getenv('LOCALAPPDATA', str(Path.home()))) / 'SpotyVManager' / 'data') if getattr(sys, 'frozen', False) else APP_DIR / 'data'
CACHE_DIR = DATA_DIR.parent / 'cache'
load_dotenv(dotenv_path=APP_DIR / '.env')

#: Credenciales
CLIENT_ID: str = os.getenv("CLIENT_ID", "")
CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
REDIRECT_URI: str = os.getenv("REDIRECT_URI", "http://127.0.0.1:8888/callback")
if REDIRECT_URI.startswith('http://localhost:'):
    REDIRECT_URI = REDIRECT_URI.replace('http://localhost:', 'http://127.0.0.1:', 1)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
AI_MODEL: str = os.getenv("AI_MODEL", "gpt-5-mini")
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "chatgpt").strip().lower()

#: Alcances Spotify
SCOPES: str = (
    "user-library-read "
    "playlist-read-private "
    "playlist-read-collaborative "
    "playlist-modify-public "
    "playlist-modify-private "
    "user-follow-read "
    "user-read-playback-position "
    "user-top-read"
)

# ---------------------------------------------------
# LOGGING
# ---------------------------------------------------
# La configuración se ha movido a app.py para un control más explícito
logger = logging.getLogger(__name__)
