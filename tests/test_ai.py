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

def test_non_latin_titles_do_not_collapse_to_empty_strings():
    suggestion={'title':'東京','artist':'歌手'}
    unrelated={'name':'大阪','artists':[{'name':'歌手'}]}
    assert match_score(suggestion,unrelated)<0.6

def test_fallback_and_duplicate():
    sp = Mock()
    sp.search.side_effect = [{'tracks': {'items': []}}, {'tracks': {'items': [TRACK]}}]
    assert find_track(sp, SONG)['id'] == 'abc'
    assert sp.search.call_args_list[0].kwargs['q'].startswith('track:')
    with patch('src.utils.ai_playlist_builder.find_track', return_value=TRACK):
        rows = resolve_suggestions(sp, [SONG, SONG])
    assert [r['selected'] for r in rows] == [True, False]

def test_invalid_response_retried_once():
    response = lambda text: SimpleNamespace(output_text=text, status='completed')
    client = Mock()
    client.responses.create.side_effect = [response('invalid'), response(json.dumps([SONG]))]
    with patch('src.utils.ai_recommender.OPENAI_API_KEY', 'test'), patch('src.utils.ai_recommender.openai.OpenAI', return_value=client):
        assert recomendar_canciones('tranquilo') == [SONG]
    assert client.responses.create.call_count == 2
    request = client.responses.create.call_args_list[0].kwargs
    assert request['store'] is False
    assert request['max_output_tokens'] == 4096
    assert len(request['input']) == 1
    assert len(client.responses.create.call_args_list[1].kwargs['input']) == 3
    client.close.assert_called_once()

@pytest.mark.parametrize('body,message', [
    ({'code': 'insufficient_quota'}, 'cuota disponible'),
    ({'code': 'credit_balance_exhausted', 'type': 'insufficient_quota'}, 'cuota disponible'),
    ({'error': {'type': 'insufficient_quota'}}, 'cuota disponible'),
    ({'code': 'rate_limit_exceeded'}, 'límite de peticiones'),
])
def test_quota_and_request_limits_have_distinct_messages(body, message):
    import httpx
    import openai
    client = Mock()
    response = httpx.Response(429, request=httpx.Request('POST', 'https://api.openai.com/v1/responses'))
    client.responses.create.side_effect = openai.RateLimitError('Limit', response=response, body=body)
    with patch('src.utils.ai_recommender.OPENAI_API_KEY', 'test'), patch('src.utils.ai_recommender.openai.OpenAI', return_value=client):
        with pytest.raises(AIError, match=message):
            recomendar_canciones('tranquilo')
    client.responses.create.assert_called_once()
    client.close.assert_called_once()

def test_missing_key_does_not_call_api():
    with patch('src.utils.ai_recommender.OPENAI_API_KEY',''),patch('src.utils.ai_recommender.openai.OpenAI') as factory:
        with pytest.raises(AIError,match='OPENAI_API_KEY'):recomendar_canciones('test')
        factory.assert_not_called()

def test_json_is_not_retried_more_than_once():
    client=Mock()
    client.responses.create.return_value=SimpleNamespace(output_text='invalid', status='completed')
    with patch('src.utils.ai_recommender.OPENAI_API_KEY','test'),patch('src.utils.ai_recommender.openai.OpenAI',return_value=client):
        with pytest.raises(AIError):recomendar_canciones('test')
    assert client.responses.create.call_count==2

def test_incomplete_response_is_not_used_or_retried():
    client = Mock()
    client.responses.create.return_value = SimpleNamespace(status='incomplete', output_text='{"songs":')
    with patch('src.utils.ai_recommender.OPENAI_API_KEY', 'test'), patch('src.utils.ai_recommender.openai.OpenAI', return_value=client):
        with pytest.raises(AIError, match='no completó'):
            recomendar_canciones('tranquilo')
    client.responses.create.assert_called_once()
    client.close.assert_called_once()
