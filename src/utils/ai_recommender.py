"""OpenAI recibe solo instrucciones del usuario y sugerencias de OpenAI."""
import json
import re
import openai
from ..config import OPENAI_API_KEY, AI_MODEL

class AIError(RuntimeError):
    pass

def parse_json(text):
    text = text.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError) as error:
        raise AIError('La IA devolvió JSON inválido. Intenta de nuevo.') from error

def parse_songs(text):
    value = parse_json(text)
    songs = value.get('songs') if isinstance(value, dict) else value
    if not isinstance(songs, list) or not songs or len(songs) > 50:
        raise AIError('La IA debe devolver entre 1 y 50 canciones.')
    result, seen = [], set()
    for song in songs:
        if not isinstance(song, dict):
            raise AIError('Una sugerencia tiene formato inválido.')
        title, artist = song.get('title'), song.get('artist')
        if not isinstance(title, str) or not isinstance(artist, str) or not title.strip() or not artist.strip():
            raise AIError('Cada canción debe incluir título y artista.')
        key = (title.strip().casefold(), artist.strip().casefold())
        if key not in seen:
            result.append({'title': title.strip(), 'artist': artist.strip()})
            seen.add(key)
    return result

def _request(messages, parser):
    if not OPENAI_API_KEY:
        raise AIError('Falta OPENAI_API_KEY en tu archivo .env. Reinicia la app tras agregarla.')
    client = openai.OpenAI(api_key=OPENAI_API_KEY, timeout=45, max_retries=0)
    conversation = [dict(message) for message in messages]
    try:
        for attempt in range(2):
            response = client.responses.create(model=AI_MODEL, max_output_tokens=4096,
                instructions='Eres un curador musical. Sigue las instrucciones del usuario. Devuelve únicamente JSON, sin Markdown.',
                input=[dict(message) for message in conversation], store=False)
            if response.status != 'completed':
                raise AIError('OpenAI no completó la respuesta. Intenta de nuevo o revisa AI_MODEL.')
            text = response.output_text
            try:
                return parser(text)
            except AIError:
                if attempt:
                    raise
                conversation.extend([{'role': 'assistant', 'content': text},
                    {'role': 'user', 'content': 'Corrige tu respuesta: devuelve JSON válido con el esquema solicitado.'}])
    except openai.AuthenticationError as error:
        raise AIError('OpenAI rechazó la API key. Revisa OPENAI_API_KEY.') from error
    except openai.RateLimitError as error:
        body = error.body if isinstance(error.body, dict) else {}
        details = body.get('error', body)
        details = details if isinstance(details, dict) else {}
        if details.get('code') == 'insufficient_quota' or details.get('type') == 'insufficient_quota':
            raise AIError('OpenAI no tiene cuota disponible para esta clave (429). Revisa saldo y límites de facturación en https://platform.openai.com/settings/organization/billing/overview. El plan de ChatGPT se gestiona por separado.') from error
        raise AIError('OpenAI alcanzó su límite de peticiones. Intenta más tarde.') from error
    except openai.APITimeoutError as error:
        raise AIError('La IA tardó demasiado. Intenta de nuevo.') from error
    except openai.APIConnectionError as error:
        raise AIError('No se pudo conectar a OpenAI.') from error
    except openai.APIStatusError as error:
        raise AIError(f'OpenAI devolvió HTTP {error.status_code}. Revisa modelo, saldo y acceso.') from error
    finally:
        client.close()

def recomendar_canciones(prompt, cantidad=15, excluir=(), orden='normal', historial=None):
    cantidad = max(1, min(int(cantidad), 50))
    instruction = {'request': prompt, 'count': cantidad,
        'order': 'inicio suave, pico de energía y cierre suave' if orden == 'arco' else 'normal',
        'exclude': list(excluir), 'schema': {'songs': [{'title': 'Título', 'artist': 'Artista'}]}}
    messages = list(historial or []) + [{'role': 'user', 'content': json.dumps(instruction, ensure_ascii=False)}]
    songs = _request(messages, parse_songs)
    excluded = {(s['title'].casefold(), s['artist'].casefold()) for s in excluir}
    return [song for song in songs if (song['title'].casefold(), song['artist'].casefold()) not in excluded][:cantidad]

def sugerir_nombre_playlist(prompt, canciones):
    def parser(text):
        value = parse_json(text)
        if not isinstance(value, dict) or not all(isinstance(value.get(k), str) and value[k].strip() for k in ('name', 'description')):
            raise AIError('Nombre o descripción inválidos.')
        return value['name'][:100], value['description'][:300]
    return _request([{'role': 'user', 'content': json.dumps({'request': prompt,
        'songs': canciones, 'schema': {'name': 'Nombre', 'description': 'Descripción'}}, ensure_ascii=False)}], parser)

def resumir_gusto(descripcion_usuario):
    def parser(text):
        value = parse_json(text)
        if not isinstance(value, dict) or not isinstance(value.get('profile'), str):
            raise AIError('Perfil inválido.')
        return value['profile']
    return _request([{'role': 'user', 'content': json.dumps({'request': 'Describe con humor mi gusto musical, sin inventar datos personales.',
        'my_description': descripcion_usuario, 'schema': {'profile': 'Perfil breve'}}, ensure_ascii=False)}], parser)
