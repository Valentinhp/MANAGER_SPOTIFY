import json
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import pytest
import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from src.utils import chatgpt_session as session
from src.utils.ai_recommender import AIError, recomendar_canciones


@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setattr(session, 'SESSION_PATH', tmp_path / 'session.bin')
    return session.SESSION_PATH


def save_profile(scopes=None, expires=None):
    state = {'host_id': 'urn:uuid:test-host', 'active': 'oaiapp_test', 'profiles': {
        'oaiapp_test': {'client_id': 'oaiapp_test', 'subject': 'user-one', 'email': 'test@example.test',
                        'access_token': 'test-access', 'refresh_token': 'test-refresh',
                        'scopes': scopes if scopes is not None else [session.DIRECT_SCOPE],
                        'expires_at': expires if expires is not None else time.time() + 3600}}}
    session._save(state)
    return state


def test_storage_round_trip_protects_tokens_on_windows(storage):
    import os
    state = save_profile()
    assert session._load() == state
    if os.name == 'nt':
        assert b'test-access' not in storage.read_bytes()
    else:
        assert storage.stat().st_mode & 0o777 == 0o600


def test_plan_permission_is_required_before_inference(storage):
    save_profile(scopes=['openid'])
    with patch.object(session.requests, 'post') as post:
        with pytest.raises(session.ChatGPTError, match='permitir'):
            session.access_token()
    post.assert_not_called()


def test_refresh_saves_rotating_tokens_atomically(storage):
    save_profile(expires=0)
    response = Mock(ok=True)
    response.json.return_value = {'access_token': 'replacement', 'refresh_token': 'rotated', 'expires_in': 3600}
    with patch.object(session.requests, 'post', return_value=response) as post:
        assert session.access_token() == 'replacement'
    assert post.call_args.kwargs['data']['client_id'] == 'oaiapp_test'
    assert 'scope' not in post.call_args.kwargs['data']
    assert session._load()['profiles']['oaiapp_test']['refresh_token'] == 'rotated'


def test_revoked_refresh_clears_tokens_and_retains_registration(storage):
    save_profile(expires=0)
    response = Mock(ok=False)
    response.json.return_value = {'error': 'invalid_grant'}
    with patch.object(session.requests, 'post', return_value=response):
        with pytest.raises(session.ChatGPTError):
            session.access_token()
    profile = session._load()['profiles']['oaiapp_test']
    assert profile['client_id'] == 'oaiapp_test'
    assert 'access_token' not in profile and 'refresh_token' not in profile


def test_temporary_refresh_failure_keeps_credentials(storage):
    original = save_profile(expires=0)
    with patch.object(session.requests, 'post', side_effect=requests.ConnectionError):
        with pytest.raises(session.ChatGPTError):
            session.access_token()
    assert session._load() == original


@pytest.fixture(scope='module')
def signing_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def test_id_token_signature_audience_and_nonce(signing_key):
    claims = {'iss': session.ISSUER, 'sub': 'user-one', 'aud': 'oaiapp_test',
              'exp': time.time() + 60, 'nonce': 'expected'}
    token = jwt.encode(claims, signing_key, algorithm='RS256')
    jwks = Mock()
    jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=signing_key.public_key())
    with patch.object(session.jwt, 'PyJWKClient', return_value=jwks):
        assert session._verify_identity(token, 'oaiapp_test', 'expected')['sub'] == 'user-one'
        with pytest.raises(session.ChatGPTError):
            session._verify_identity(token, 'wrong-client', 'expected')
        with pytest.raises(session.ChatGPTError):
            session._verify_identity(token, 'oaiapp_test', 'wrong-nonce')


def callback_browser(captured, change_client=None):
    def open_browser(url):
        params = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
        captured.update(params)
        def callback():
            values = {'code': 'test-code', 'state': params['state'], 'client_id': change_client or 'oaiapp_test'}
            requests.get(params['redirect_uri'] + '?' + urlencode(values), timeout=5)
        thread = threading.Thread(target=callback)
        thread.start()
        captured['thread'] = thread
        return True
    return open_browser


def test_dynamic_registration_pkce_callback_and_protected_storage(storage):
    captured = {}
    tokens = {'access_token': 'test-access', 'refresh_token': 'test-refresh',
              'id_token': 'test-id-token', 'scope': session.SCOPES, 'expires_in': 3600}
    identity = {'sub': 'user-one', 'email': 'test@example.test'}
    with patch.object(session.webbrowser, 'open', side_effect=callback_browser(captured)), \
         patch.object(session, '_token_request', return_value=tokens) as exchange, \
         patch.object(session, '_verify_identity', return_value=identity) as verify:
        profile = session.connect()
    captured['thread'].join()
    assert captured['client_id'] == 'dynamic_agent_client'
    assert captured['agent_name_hint'] == 'SpotyVManager'
    assert captured['code_challenge_method'] == 'S256'
    assert captured['redirect_uri'].startswith('http://127.0.0.1:')
    assert captured['redirect_uri'].endswith('/auth/callback')
    assert exchange.call_args.args[0]['client_id'] == 'oaiapp_test'
    assert exchange.call_args.args[0]['redirect_uri'] == captured['redirect_uri']
    assert verify.call_args.args[2] == captured['nonce']
    assert profile['enabled'] is True
    assert session._load()['active'] == 'oaiapp_test'


def test_returning_registration_rejects_changed_client(storage):
    original = save_profile()
    captured = {}
    with patch.object(session.webbrowser, 'open', side_effect=callback_browser(captured, 'other-client')), \
         patch.object(session, '_token_request') as exchange:
        with pytest.raises(session.ChatGPTError, match='registro distinto'):
            session.connect()
    captured['thread'].join()
    exchange.assert_not_called()
    assert captured['client_id'] == 'oaiapp_test'
    assert captured['ext_agent_host_id'] == original['host_id']
    assert 'agent_name_hint' not in captured
    assert session._load() == original


def stream_client(events):
    client = Mock()
    stream = Mock()
    stream.__enter__ = Mock(return_value=iter(events))
    stream.__exit__ = Mock(return_value=False)
    client.responses.create.return_value = stream
    return client


def test_chatgpt_generation_uses_plan_with_supported_request_only():
    songs = [{'title': 'Song', 'artist': 'Artist'}]
    client = stream_client([
        SimpleNamespace(type='response.output_text.delta', delta=json.dumps({'songs': songs})),
        SimpleNamespace(type='response.completed'),
    ])
    with patch('src.utils.ai_recommender.AI_PROVIDER', 'chatgpt'), \
         patch('src.utils.ai_recommender.OPENAI_API_KEY', ''), \
         patch.object(session, 'inference_credentials', return_value=('oauth-token', 'allowed-model')), \
         patch('src.utils.ai_recommender.openai.OpenAI', return_value=client) as factory:
        assert recomendar_canciones('relax') == songs
    assert factory.call_args.kwargs['api_key'] == 'oauth-token'
    options = client.responses.create.call_args.kwargs
    assert options['store'] is False and options['stream'] is True
    assert options['model'] == 'allowed-model'
    assert 'max_output_tokens' not in options
    client.close.assert_called_once()


@pytest.mark.parametrize('events,match', [
    ([SimpleNamespace(type='response.output_text.delta', delta='partial')], 'interrumpió'),
    ([SimpleNamespace(type='response.failed', response=SimpleNamespace(error=SimpleNamespace(
        code='subscription_sharing_usage_limit_exceeded')))], 'límite de uso'),
    ([SimpleNamespace(type='response.incomplete')], 'no completó'),
])
def test_incomplete_or_failed_stream_never_creates_playlist_or_uses_api(events, match):
    client = stream_client(events)
    with patch('src.utils.ai_recommender.AI_PROVIDER', 'chatgpt'), \
         patch.object(session, 'inference_credentials', return_value=('oauth-token', 'allowed-model')), \
         patch('src.utils.ai_recommender.openai.OpenAI', return_value=client):
        with pytest.raises(AIError, match=match):
            recomendar_canciones('relax')
    client.responses.create.assert_called_once()
    client.close.assert_called_once()


def test_catalog_is_filtered_and_selected_slug_is_preserved(storage):
    save_profile()
    session.select_model('second')
    response = Mock(ok=True)
    response.json.return_value = {'models': [
        {'slug': 'hidden', 'visibility': 'hide'},
        {'slug': 'first', 'visibility': 'list'},
        {'slug': 'second', 'visibility': 'list'},
    ]}
    with patch.object(session.requests, 'get', return_value=response):
        assert session.inference_credentials() == ('test-access', 'second')


def test_sign_out_keeps_registration_and_removes_credentials(storage):
    save_profile()
    with patch.object(session.requests, 'post', side_effect=requests.ConnectionError):
        assert session.disconnect() is False
    profile = session._load()['profiles']['oaiapp_test']
    assert profile['client_id'] == 'oaiapp_test'
    assert 'access_token' not in profile and 'refresh_token' not in profile
