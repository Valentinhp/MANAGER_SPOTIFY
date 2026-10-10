"""Resuelve nombres de Spotify sin enviar metadatos a la IA."""
from .spotify_utils import obtener_playlists_usuario
from .progress import report_progress


def resolve_playlist_names(sp, ids, known=None):
    names = dict(known or {})
    if known is None:
        try:
            names.update((pid, name) for pid, name, _ in obtener_playlists_usuario(sp))
        except Exception:
            pass
    missing = list(dict.fromkeys(pid for pid in ids if pid and pid not in names))
    for index, pid in enumerate(missing):
        report_progress(index, len(missing), 'Consultando nombres de playlists…')
        try:
            name = sp.playlist(pid, fields='name').get('name')
            if isinstance(name, str) and name.strip():
                names[pid] = name
        except Exception:
            pass  # Puede ser una playlist eliminada o sin acceso.
    return names


def playlist_label(pid, names=None, saved=None):
    return (names or {}).get(pid) or saved or f'Playlist no disponible ({pid})'
