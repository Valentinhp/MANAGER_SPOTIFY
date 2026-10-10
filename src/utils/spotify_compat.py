"""Endpoints actuales, con respuestas compatibles con las vistas existentes."""
import threading
import time
from copy import deepcopy
from collections import OrderedDict
from .api_decorator import handle_spotify_errors

_cache = OrderedDict()
_lock = threading.Lock()

@handle_spotify_errors()
def _request(sp, method, path, **kwargs):
    return getattr(sp, method)(path, **kwargs)

def search_paginated(sp, q, type, total, offset=0):
    if type not in ('track', 'artist', 'album', 'playlist', 'show', 'episode', 'audiobook'):
        raise ValueError('Busca un tipo de contenido a la vez.')
    total = max(0, min(int(total), 1000 - offset))
    key = type + 's'
    items = []
    page = {}
    while len(items) < total:
        result = sp.search(q=q, type=type, limit=min(10, total-len(items)), offset=offset+len(items))
        page = result.get(key, {})
        batch = page.get('items') or []
        if not batch:
            break
        items.extend(batch)
        if not page.get('next'):
            break
    return {key: {**page, 'items': items[:total], 'offset': offset, 'limit': total}}

def cached_entities(sp, kind, ids):
    values = []
    for entity_id in ids:
        key = (sp, kind, entity_id)
        with _lock:
            value = _cache.get(key)
        if value is None:
            value = getattr(sp, kind)(entity_id)
            if value is not None:
                with _lock:
                    _cache[key] = deepcopy(value)
                    if len(_cache) > 2000:
                        _cache.popitem(last=False)
            time.sleep(0.1)
        values.append(deepcopy(value))
    return {kind+'s': values}

def create_playlist(sp, name, public=False, description=''):
    return _request(sp, '_post', 'me/playlists', payload={'name': name, 'public': public, 'description': description})

def read_items(sp, playlist_id, fields=None, limit=50, offset=0):
    params = {'limit': min(limit, 50), 'offset': offset, 'additional_types': 'track,episode'}
    if fields:
        params['fields'] = fields.replace('track(', 'item(')
    result = _request(sp, '_get', f'playlists/{playlist_id}/items', **params)
    for row in result.get('items') or []:
        if row:
            row['track'] = row.get('item', row.get('track'))
    return result

def add_items(sp, playlist_id, uris):
    uris = [sp._get_uri(uri, 'track') for uri in uris]
    result = None
    for start in range(0, len(uris), 100):
        result = _request(sp, '_post', f'playlists/{playlist_id}/items', payload={'uris': uris[start:start+100]})
    return result

def remove_items(sp, playlist_id, items, snapshot_id=None):
    result = None
    items = sorted(items, key=lambda x: max(x.get('positions', [-1])), reverse=True)
    for start in range(0, len(items), 100):
        payload = {'items': items[start:start+100]}
        if snapshot_id:
            payload['snapshot_id'] = snapshot_id
        result = _request(sp, '_delete', f'playlists/{playlist_id}/items', payload=payload)
        snapshot_id = (result or {}).get('snapshot_id')
    return result

def replace_items(sp, playlist_id, uris):
    uris = [sp._get_uri(uri, 'track') for uri in uris]
    result = _request(sp, '_put', f'playlists/{playlist_id}/items', payload={'uris': uris[:100]})
    if len(uris) > 100:
        result = add_items(sp, playlist_id, uris[100:])
    return result

def remove_from_library(sp, uris):
    result = None
    for start in range(0, len(uris), 40):
        result = _request(sp, '_delete', 'me/library', uris=','.join(uris[start:start+40]))
    return result
