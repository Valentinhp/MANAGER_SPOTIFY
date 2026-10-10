import logging
from difflib import SequenceMatcher
from .spotify_utils import _normalize_str, user_playlist_create, playlist_add_items, search

logger = logging.getLogger(__name__)
from .progress import report_progress

def match_score(suggestion, track):
    title = SequenceMatcher(None, _normalize_str(suggestion['title']), _normalize_str(track.get('name', ''))).ratio()
    artist = max((SequenceMatcher(None, _normalize_str(suggestion['artist']), _normalize_str(a.get('name', ''))).ratio()
        for a in track.get('artists', [])), default=0)
    return min(title, artist)

def find_track(sp, suggestion, threshold=0.6):
    title = suggestion['title'].replace('"', ' ')
    artist = suggestion['artist'].replace('"', ' ')
    for query in (f'track:"{title}" artist:"{artist}"', f'{title} {artist}'):
        response = search(sp, query, 'track', 10)
        candidates = [track for track in response.get('tracks', {}).get('items', []) if track and track.get('id') and track.get('uri')]
        best = max(candidates, key=lambda t: match_score(suggestion, t), default=None)
        if best and match_score(suggestion, best) >= threshold:
            return best
    logger.info('Sugerencia de IA no encontrada: %s — %s', suggestion['title'], suggestion['artist'])
    return None

def resolve_suggestions(sp, suggestions):
    rows, seen = [], set()
    for index,suggestion in enumerate(suggestions):
        report_progress(index,len(suggestions),f'Buscando {index+1}/{len(suggestions)}: {suggestion["title"]} — {suggestion["artist"]}')
        track = find_track(sp, suggestion)
        duplicate = bool(track and track['id'] in seen)
        if track:
            seen.add(track['id'])
        rows.append({'suggestion': suggestion, 'track': track, 'selected': bool(track and not duplicate),
            'status': 'Duplicada' if duplicate else 'Encontrada' if track else 'No encontrada'})
        report_progress(index+1,len(suggestions),f'{index+1}/{len(suggestions)} canciones comprobadas')
    return rows

def build_playlist(sp, name, description, rows, public=False):
    uris = list(dict.fromkeys(row['track']['uri'] for row in rows if row.get('selected') and row.get('track')))
    if not uris:
        raise ValueError('Selecciona al menos una canción encontrada.')
    playlist = user_playlist_create(sp, '', name.strip() or 'Radio de Ánimo', public, description)
    try:
        playlist_add_items(sp, playlist['id'], uris)
    except Exception as error:
        raise RuntimeError(f'Se creó la playlist «{playlist.get("name") or name}» ({playlist["id"]}), pero falló al agregar canciones. Revisa esa playlist antes de volver a crearla.') from error
    return playlist
