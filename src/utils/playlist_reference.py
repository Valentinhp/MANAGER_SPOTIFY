"""Read real playlist tracks and prepare bounded musical context."""
from .spotify_utils import playlist_items


def load_reference(sp, playlist_id):
    tracks, seen, offset = [], set(), 0
    while True:
        response = playlist_items(sp, playlist_id, limit=50, offset=offset)
        if not isinstance(response, dict):
            raise ValueError('No se pudo leer la playlist de Spotify.')
        items = response.get('items', [])
        for row in items:
            track = (row.get('item') or row.get('track')) if row else None
            if not track or track.get('type', 'track') != 'track' or not track.get('id') or not track.get('artists'):
                continue
            if track['id'] not in seen:
                seen.add(track['id'])
                tracks.append(track)
        if not response.get('next'):
            break
        if not items:
            raise ValueError('Spotify devolvió una página vacía incompleta.')
        offset += len(items)
    if not tracks:
        raise ValueError('Esta playlist no contiene canciones accesibles para usar como referencia.')
    return tracks


def reference_songs(tracks):
    return [{'title': t['name'], 'artist': ', '.join(a['name'] for a in t['artists'])} for t in tracks]


def reference_sample(tracks, limit=100):
    songs = reference_songs(tracks)
    if len(songs) <= limit:
        return songs
    return [songs[i * (len(songs) - 1) // (limit - 1)] for i in range(limit)]
