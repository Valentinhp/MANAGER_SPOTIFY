from unittest.mock import Mock, patch

import pytest
import requests
from spotipy.exceptions import SpotifyException

from src.utils.api_decorator import handle_spotify_errors
from src.utils.spotify_rate_limit import RateLimitedSpotify, SpotifyRateLimitError, retry_seconds
from src.utils.spotify_utils import obtener_canciones_artista


def test_actual_http_429_preserves_wait_and_survives_restart(tmp_path):
    path = tmp_path / 'cooldown.json'
    client = RateLimitedSpotify(cooldown_path=path, client_id='test', auth='offline', interval=0)
    response = requests.Response()
    response.status_code = 429
    response.url = 'https://api.spotify.com/v1/artists/test'
    response.headers['Retry-After'] = '79325'
    response._content = b'{"error":{"message":"Too many requests"}}'
    with patch.object(client._session, 'request', return_value=response) as request:
        with pytest.raises(SpotifyRateLimitError, match='22 h'):
            client.artist('test')
        with pytest.raises(SpotifyRateLimitError):
            client.artist('next')
        assert request.call_count == 1
    restarted = RateLimitedSpotify(cooldown_path=path, client_id='test', auth='offline', interval=0)
    with patch.object(restarted._session, 'request') as request:
        with pytest.raises(SpotifyRateLimitError):
            restarted.artist('next')
        request.assert_not_called()


def test_long_or_missing_retry_after_never_sleeps_or_replays():
    for headers in ({'Retry-After': '79325'}, None):
        operation = Mock(side_effect=SpotifyException(429, -1, 'limited', headers=headers))
        @handle_spotify_errors()
        def wrapped():
            return operation()
        with patch('src.utils.api_decorator.time.sleep') as sleep:
            with pytest.raises(SpotifyRateLimitError):
                wrapped()
            sleep.assert_not_called()
            operation.assert_called_once()


def test_album_limit_does_not_continue_to_other_sources():
    sp = Mock()
    sp.artist.return_value = {'name': 'Artista'}
    sp.artist_albums.side_effect = SpotifyRateLimitError(79325)
    with pytest.raises(SpotifyRateLimitError):
        obtener_canciones_artista(sp, 'artist')
    sp.artist_albums.assert_called_once()
    sp.search.assert_not_called()


def test_album_tracks_need_no_individual_requests_or_search_repagination():
    sp = Mock()
    sp.artist.return_value = {'name': 'Artista'}
    album = {'id': 'album', 'release_date': '2026-01-01'}
    sp.artist_albums.return_value = {'items': [album], 'next': None}
    sp.album_tracks.return_value = {'items': [{'id': 'song', 'uri': 'spotify:track:song', 'name': 'Canción', 'artists': [{'id': 'artist'}], 'duration_ms': 1}], 'next': None}
    with patch('src.utils.spotify_utils.search_paginated', return_value={'tracks': {'items': [], 'next': 'unused'}}), patch('src.utils.spotify_utils.time.sleep'):
        result = obtener_canciones_artista(sp, 'artist')
    assert result[0]['album']['release_date'] == '2026-01-01'
    sp.album_tracks.assert_called_once()
    sp.track.assert_not_called()
    sp.next.assert_not_called()


def test_invalid_retry_after_uses_safe_fallback():
    assert retry_seconds({'retry-after': '79325'}) == 79325
    for value in ('invalid', 'nan', 'inf'):
        assert retry_seconds({'Retry-After': value}) == 60
