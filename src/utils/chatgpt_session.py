"""OAuth oficial de ChatGPT para uso del plan; no lee sesiones de otras apps."""
import base64
import ctypes
import hashlib
import json
import os
import secrets
import threading
import time
import uuid
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
import requests
from ..config import DATA_DIR

AUTH_URL = 'https://auth.openai.com/api/accounts/authorize'
TOKEN_URL = 'https://auth.openai.com/api/accounts/oauth/token'
RESOURCE = 'https://api.openai.com/v1'
ISSUER = 'https://auth.openai.com'
JWKS_URL = ISSUER + '/.well-known/jwks.json'
DIRECT_SCOPE = 'chatgpt.tokens.use.direct'
SCOPES = 'openid profile email offline_access resource.invoke ' + DIRECT_SCOPE
SESSION_PATH = DATA_DIR / 'chatgpt-session.bin'
_THREAD_LOCK = threading.RLock()


class ChatGPTError(RuntimeError):
    pass


def _protect(data, decrypt=False):
    if os.name != 'nt':
        return data  # En Unix, archivo privado con permisos 0600.
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)
    fn = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wintypes.BOOL
    if not fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ChatGPTError('Windows no pudo proteger o leer la sesión de ChatGPT.')
    try:
        return ctypes.string_at(result.data, result.length)
    finally:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(result.data)


@contextmanager
def _locked():
    """Serializa también renovaciones entre procesos para tokens rotativos."""
    with _THREAD_LOCK:
        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_PATH.with_suffix('.lock'), 'a+b') as lock:
            if os.name == 'nt':
                import msvcrt
                lock.seek(0, 2)
                if lock.tell() == 0:
                    lock.write(b'0'); lock.flush()
                deadline = time.monotonic() + 320
                while True:
                    lock.seek(0)
                    try:
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise ChatGPTError('Hay otra conexión a ChatGPT en curso. Intenta más tarde.')
                        time.sleep(.1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == 'nt':
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _load():
    if not SESSION_PATH.exists():
        return {'host_id': 'urn:uuid:' + str(uuid.uuid4()), 'profiles': {}, 'active': None}
    try:
        return json.loads(_protect(SESSION_PATH.read_bytes(), decrypt=True))
    except (OSError, ValueError) as error:
        raise ChatGPTError('No se pudo leer la sesión local de ChatGPT.') from error


def _save(state):
    data = _protect(json.dumps(state).encode('utf-8'))
    temporary = SESSION_PATH.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)
    temporary.replace(SESSION_PATH)
    if os.name != 'nt':
        SESSION_PATH.chmod(0o600)


def _verify_identity(id_token, client_id, nonce):
    try:
        key = jwt.PyJWKClient(JWKS_URL, timeout=20).get_signing_key_from_jwt(id_token)
        identity = jwt.decode(id_token, key.key, algorithms=['RS256'], audience=client_id,
                              issuer=ISSUER, options={'require': ['exp', 'iss', 'aud', 'sub', 'nonce']})
        if not secrets.compare_digest(str(identity['nonce']), nonce):
            raise ChatGPTError('La identidad de ChatGPT no coincide con este inicio de sesión.')
        return identity
    except jwt.PyJWTError as error:
        raise ChatGPTError('No se pudo verificar la identidad de ChatGPT. Inicia sesión de nuevo.') from error


def _token_request(payload):
    try:
        response = requests.post(TOKEN_URL, data=payload, timeout=25)
        body = response.json()
    except (requests.RequestException, ValueError) as error:
        raise ChatGPTError('No se pudo contactar al servidor de inicio de sesión de ChatGPT.') from error
    if not response.ok:
        error = body.get('error', 'unknown_error') if isinstance(body, dict) else 'unknown_error'
        code = error.get('code') or error.get('type') if isinstance(error, dict) else error
        failure = ChatGPTError(f'ChatGPT rechazó la sesión ({code}). Pulsa Continue with ChatGPT para reconectar.')
        failure.code = code
        raise failure
    if not isinstance(body, dict) or not body.get('access_token'):
        raise ChatGPTError('ChatGPT devolvió una sesión incompleta.')
    return body


def _merge_tokens(profile, tokens):
    profile = dict(profile)
    for key in ('access_token', 'refresh_token', 'id_token'):
        if tokens.get(key):
            profile[key] = tokens[key]
    if 'scope' in tokens:
        profile['scopes'] = tokens['scope'].split()
    profile['expires_at'] = time.time() + float(tokens.get('expires_in', 3600))
    return profile


def connect(profile_id=None, new=False):
    """El usuario inicia este flujo con el botón Continue with ChatGPT."""
    with _locked():
        state = _load()
        _save(state)  # Persiste el host antes del primer intento.
        profiles = state['profiles']
        selected = None if new else (profile_id or state.get('active') or next(iter(profiles), None))
        old = profiles.get(selected, {})
        verifier, nonce, expected_state = (secrets.token_urlsafe(48) for _ in range(3))
        result = {}

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass  # La URL contiene el código de autorización.

            def do_GET(self):
                url = urlsplit(self.path)
                if url.path != '/auth/callback':
                    self.send_error(404); return
                values = {key: items[0] for key, items in parse_qs(url.query).items()}
                if not secrets.compare_digest(values.get('state', ''), expected_state):
                    self.send_error(400, 'Invalid state'); return
                result.update(values)
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write('Puedes cerrar esta ventana y volver a SpotyVManager.'.encode('utf-8'))

        with HTTPServer(('127.0.0.1', 0), Callback) as server:
            server.timeout = .5
            redirect = f'http://127.0.0.1:{server.server_port}/auth/callback'
            params = {'client_id': selected or 'dynamic_agent_client', 'response_type': 'code',
                      'redirect_uri': redirect, 'scope': SCOPES, 'resource': RESOURCE,
                      'state': expected_state, 'nonce': nonce, 'ext_agent_host_id': state['host_id'],
                      'code_challenge_method': 'S256',
                      'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')}
            if not selected:
                params['agent_name_hint'] = 'SpotyVManager'
            elif old.get('id_token'):
                params['id_token_hint'] = old['id_token']
            if old.get('subject') and DIRECT_SCOPE not in old.get('scopes', []):
                params['prompt'] = 'consent'
            if not webbrowser.open(AUTH_URL + '?' + urlencode(params)):
                raise ChatGPTError('No se pudo abrir el navegador. Configura un navegador predeterminado.')
            deadline = time.monotonic() + 240
            while not result and time.monotonic() < deadline:
                server.handle_request()
        if not result:
            raise ChatGPTError('Se agotó el tiempo para conectar ChatGPT. Intenta de nuevo.')
        if result.get('error'):
            raise ChatGPTError('No se autorizó el uso de ChatGPT. Puedes volver a conectar cuando quieras.')
        issued = result.get('client_id', selected)
        if not issued or issued == 'dynamic_agent_client' or (selected and issued != selected):
            raise ChatGPTError('ChatGPT devolvió un registro distinto del solicitado.')
        if not result.get('code'):
            raise ChatGPTError('No se recibió el código de autorización de ChatGPT.')
        if issued not in profiles:
            profiles[issued] = {'client_id': issued}
            _save(state)  # Conserva el registro si un código expira durante el intercambio.
        tokens = _token_request({'grant_type': 'authorization_code', 'client_id': issued,
                                 'code': result['code'], 'code_verifier': verifier,
                                 'redirect_uri': redirect, 'resource': RESOURCE})
        identity = _verify_identity(tokens.get('id_token', ''), issued, nonce)
        if old.get('subject') and identity['sub'] != old['subject']:
            raise ChatGPTError('La cuenta no coincide. Usa Añadir cuenta para conectar otra.')
        profile = _merge_tokens({'client_id': issued, 'subject': identity['sub'],
                                 'email': identity.get('email', ''), 'scopes': []}, tokens)
        profiles[issued] = profile
        state['active'] = issued
        _save(state)
        return profile_summary(profile)


def profile_summary(profile):
    return {'id': profile['client_id'], 'label': (profile.get('email') or 'Registro pendiente') + ' · ' + profile['client_id'][-6:],
            'connected': bool(profile.get('access_token')), 'enabled': DIRECT_SCOPE in profile.get('scopes', [])}


def accounts():
    # Lectura atómica sin esperar el bloqueo de un inicio de sesión en curso.
    state = _load()
    return [profile_summary(p) for p in state['profiles'].values()], state.get('active')


def model_preference():
    state = _load()
    return state['profiles'].get(state.get('active'), {}).get('model')


def select_account(profile_id):
    with _locked():
        state = _load()
        if profile_id not in state['profiles']:
            raise ChatGPTError('La cuenta de ChatGPT ya no está disponible.')
        state['active'] = profile_id
        _save(state)


def access_token():
    with _locked():
        state = _load()
        profile = state['profiles'].get(state.get('active'), {})
        if not profile.get('access_token'):
            raise ChatGPTError('Pulsa Continue with ChatGPT para conectar tu plan. No necesitas una API key.')
        if DIRECT_SCOPE not in profile.get('scopes', []):
            raise ChatGPTError('La cuenta está conectada, pero falta permitir el uso del plan. Pulsa Continue with ChatGPT.')
        if profile.get('expires_at', 0) <= time.time() + 60:
            if not profile.get('refresh_token'):
                raise ChatGPTError('La sesión expiró. Pulsa Continue with ChatGPT.')
            try:
                tokens = _token_request({'grant_type': 'refresh_token', 'client_id': profile['client_id'],
                                         'refresh_token': profile['refresh_token'], 'resource': RESOURCE})
            except ChatGPTError as error:
                if getattr(error, 'code', '') in ('invalid_grant', 'invalid_refresh_token', 'token_expired',
                                                  'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused'):
                    for key in ('access_token', 'refresh_token', 'id_token'):
                        profile.pop(key, None)
                    _save(state)
                raise
            profile = _merge_tokens(profile, tokens)
            state['profiles'][profile['client_id']] = profile
            _save(state)
            if DIRECT_SCOPE not in profile.get('scopes', []):
                raise ChatGPTError('ChatGPT retiró el permiso de usar el plan. Reconecta tu cuenta.')
        return profile['access_token']


def available_models(token=None):
    try:
        response = requests.get(RESOURCE + '/models', headers={'Authorization': 'Bearer ' + (token or access_token())}, timeout=25)
        if not response.ok:
            raise ChatGPTError(f'No se pudo consultar modelos de ChatGPT (HTTP {response.status_code}). Reconecta o intenta más tarde.')
        models = response.json().get('models', [])
        visible = [model for model in models if model.get('visibility') == 'list' and model.get('slug')]
        if not visible:
            raise ChatGPTError('Esta cuenta no ofrece modelos para el uso del plan en la app.')
        return visible
    except (requests.RequestException, ValueError) as error:
        raise ChatGPTError('No se pudo consultar los modelos disponibles de ChatGPT.') from error


def inference_credentials():
    with _locked():
        expected_account = _load().get('active')
    token = access_token()
    models = available_models(token)
    with _locked():
        state = _load()
        if state.get('active') != expected_account:
            raise ChatGPTError('Cambiaste de cuenta durante la solicitud. Intenta de nuevo.')
        profile = state['profiles'][state['active']]
        if profile.get('access_token') != token:
            raise ChatGPTError('La sesión cambió durante la solicitud. Intenta de nuevo.')
        selected = profile.get('model')
        if selected and any(model['slug'] == selected for model in models):
            return token, selected
        selected = models[0]['slug']
        profile['model'] = selected
        _save(state)
        return token, selected


def select_model(slug):
    with _locked():
        state = _load()
        profile = state['profiles'].get(state.get('active'))
        if not profile:
            raise ChatGPTError('Conecta ChatGPT antes de elegir un modelo.')
        profile['model'] = slug
        _save(state)


def disconnect():
    with _locked():
        state = _load()
        profile = state['profiles'].get(state.get('active'), {})
        revoked = not profile.get('refresh_token')
        if not revoked:
            try:
                response = requests.post(ISSUER + '/api/accounts/oauth/revoke', data={
                    'token': profile['refresh_token'], 'token_type_hint': 'refresh_token',
                    'client_id': profile['client_id']}, timeout=20)
                revoked = response.status_code == 200
            except requests.RequestException:
                pass
        for key in ('access_token', 'refresh_token', 'id_token'):
            profile.pop(key, None)
        _save(state)
        return revoked
