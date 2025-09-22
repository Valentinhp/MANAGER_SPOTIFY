from functools import wraps
import logging
import time
from spotipy.exceptions import SpotifyException
from requests.exceptions import ReadTimeout, Timeout

logger = logging.getLogger(__name__)

def handle_spotify_errors(max_retries=3):
    """
    A decorator to handle Spotify API exceptions gracefully, with retry for rate limiting.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except ReadTimeout as e:
                    logger.error(f"TIMEOUT (ReadTimeout) en '{func.__name__}': {e}")
                    return None
                except Timeout as e:
                    logger.error(f"TIMEOUT (requests.exceptions.Timeout) en '{func.__name__}': {e}")
                    return None
                except SpotifyException as e:
                    if e.http_status == 429:
                        retries += 1
                        retry_after = e.headers.get('Retry-After')
                        # Default to 1 second if header is not present
                        wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 1
                        
                        logger.warning(
                            f"Límite de peticiones de Spotify alcanzado. Intento {retries}/{max_retries}. "
                            f"Reintentando en {wait_time} segundos. (Función: {func.__name__})"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Error de API de Spotify en '{func.__name__}': {e}")
                        return None # Stop on other Spotify errors
                except Exception as e:
                    logger.error(f"Error inesperado en '{func.__name__}': {e}")
                    return None # Stop on other unexpected errors
            
            logger.error(f"La función '{func.__name__}' falló después de {max_retries} intentos debido a límites de peticiones.")
            return None
        return wrapper
    return decorator