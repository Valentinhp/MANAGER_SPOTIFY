"""Respeta la espera de Spotify sin bloquear la interfaz ni repetir operaciones."""
import json
import logging
import math
import threading
import time
from pathlib import Path

import requests
from spotipy import Spotify
from spotipy.exceptions import SpotifyException

logger = logging.getLogger(__name__)


def retry_seconds(headers):
    try:
        value = float(requests.structures.CaseInsensitiveDict(headers or {}).get('Retry-After', 60))
        return max(0, value) if math.isfinite(value) else 60
    except (TypeError, ValueError):
        return 60


class SpotifyRateLimitError(RuntimeError):
    def __init__(self, seconds):
        self.seconds = max(0, seconds)
        minutes = max(1, math.ceil(self.seconds / 60))
        hours, minutes = divmod(minutes, 60)
        duration = f'{hours} h {minutes} min' if hours else f'{minutes} min'
        super().__init__(f'Spotify limitó las peticiones (429). Espera aproximadamente {duration} antes de volver a sincronizar. Lo añadido se conserva.')


class RateLimitedSpotify(Spotify):
    """Serializa peticiones y guarda el plazo indicado por Retry-After."""
    def __init__(self, *, cooldown_path, client_id, interval=.35, **kwargs):
        self._cooldown_path = Path(cooldown_path)
        self._client_id = client_id
        self._request_lock = threading.Lock()
        self._interval = interval
        self._last_request = 0
        self._blocked_until = 0
        try:
            saved = json.loads(self._cooldown_path.read_text(encoding='utf-8'))
            if saved.get('client_id') == client_id:
                deadline = float(saved['until'])
                if math.isfinite(deadline):
                    self._blocked_until = deadline
        except (OSError, ValueError, KeyError, TypeError):
            pass
        # El adaptador predeterminado de Spotipy pierde las cabeceras del 429
        # al convertirlo en RetryError, incluso cuando retries=0.
        kwargs['requests_session'] = requests.Session()
        super().__init__(**kwargs)

    def _internal_call(self, method, url, payload, params):
        with self._request_lock:
            remaining = self._blocked_until - time.time()
            if remaining > 0:
                raise SpotifyRateLimitError(remaining)
            delay = self._interval - (time.monotonic() - self._last_request)
            if delay > 0:
                time.sleep(delay)
            self._last_request = time.monotonic()
            try:
                return super()._internal_call(method, url, payload, params)
            except SpotifyException as error:
                if error.http_status != 429:
                    raise
                seconds = retry_seconds(error.headers)
                self._blocked_until = time.time() + seconds
                try:
                    self._cooldown_path.parent.mkdir(parents=True, exist_ok=True)
                    self._cooldown_path.write_text(json.dumps({'client_id': self._client_id, 'until': self._blocked_until}), encoding='utf-8')
                except OSError:
                    logger.warning('No se pudo guardar la espera de Spotify; se respeta durante esta sesión.')
                raise SpotifyRateLimitError(seconds) from error
