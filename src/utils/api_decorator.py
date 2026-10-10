from functools import wraps
import logging
import threading
import time
from spotipy.exceptions import SpotifyException
from requests.exceptions import Timeout, ConnectionError

logger = logging.getLogger(__name__)

class SpotifyAccessError(RuntimeError):
    pass

def handle_spotify_errors(max_retries=3):
    """Reintenta 429 y propaga errores para mostrarlos desde el hilo de Tk."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except SpotifyException as error:
                    logger.error('Spotify HTTP %s en %s', error.http_status, func.__name__)
                    if error.http_status == 429 and attempt < max_retries:
                        if threading.current_thread() is threading.main_thread():
                            raise RuntimeError('Ejecuta la operaci?n de red en segundo plano.') from error
                        try:
                            wait = max(0, float((error.headers or {}).get('Retry-After', 1)))
                        except (TypeError, ValueError):
                            wait = 1
                        time.sleep(wait)
                        continue
                    if error.http_status == 403:
                        raise SpotifyAccessError('Spotify deneg? acceso (403). Revisa Premium del propietario, usuarios autorizados, permisos y propiedad de la playlist.') from error
                    if error.http_status == 429:
                        raise RuntimeError('Spotify limita las peticiones. Intenta m?s tarde.') from error
                    raise
                except (Timeout, ConnectionError) as error:
                    raise RuntimeError('No se pudo conectar a Spotify. Revisa tu conexi?n.') from error
        return wrapper
    return decorator
