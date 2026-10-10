import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest
from src.utils.ai_recommender import AIError, parse_songs, recomendar_canciones
from src.utils.ai_playlist_builder import match_score, resolve_suggestions, find_track

SONG = {'title': 'Canción', 'artist': 'Artista'}
TRACK = {'id': 'abc', 'uri': 'spotify:track:abc', 'name': 'Cancion', 'artists': [{'name': 'Artista'}]}

def test_json_fences_and_duplicates():
    assert parse_songs('```json\n'+json.dumps({'songs': [SONG, SONG]})+'\n```') == [SONG]

@pytest.mark.parametrize('text', ['no json', '{}', '[]', '[null]', '[{"title": "X", "artist": ""}]'])
def test_invalid_json(text):
    with pytest.raises(AIError):
        parse_songs(text)

def test_matching_requires_both_fields():
    assert match_score(SONG, TRACK) == 1
    assert match_score(SONG, {**TRACK, 'artists': [{'name': 'XYZ'}]}) < 0.6

def test_fallback_and_duplicate():
    sp = Mock()
    sp.search.side_effect = [{'tracks': {'items': []}}, {'tracks': {'items': [TRACK]}}]
    assert find_track(sp, SONG)['id'] == 'abc'
    assert sp.search.call_args_list[0].kwargs['q'].startswith('track:')
    with patch('src.utils.ai_playlist_builder.find_track', return_value=TRACK):
        rows = resolve_suggestions(sp, [SONG, SONG])
    assert [r['selected'] for r in rows] == [True, False]

def test_invalid_response_retried_once():
    response = lambda text: SimpleNamespace(content=[SimpleNamespace(type='text', text=text)])
    client = Mock()
    client.messages.create.side_effect = [response('invalid'), response(json.dumps([SONG]))]
    with patch('src.utils.ai_recommender.ANTHROPIC_API_KEY', 'test'), patch('src.utils.ai_recommender.anthropic.Anthropic', return_value=client):
        assert recomendar_canciones('tranquilo') == [SONG]
    assert client.messages.create.call_count == 2
    client.close.assert_called_once()
