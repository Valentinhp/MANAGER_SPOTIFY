"""
Funciones de uso general (playlists, podcasts, artistas…) - VERSIÓN OPTIMIZADA
"""
from __future__ import annotations
import time
import unicodedata
import requests
from requests.exceptions import ReadTimeout
from typing import List, Tuple, Set, Dict, Optional
from spotipy import Spotify
from collections import defaultdict

# Asumiendo que tienes una configuración de logger en otro archivo
# from ..config import logger
# Si no, puedes usar el logger básico de Python:
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Decorador para manejo de errores (asumiendo que lo tienes definido en otro lugar)
# from .api_decorator import handle_spotify_errors
# Si no, define un decorador dummy para que el código corra:
from .api_decorator import handle_spotify_errors
from .spotify_compat import (search_paginated, cached_entities, create_playlist, read_items, add_items, remove_items, replace_items, remove_from_library)


def _normalize_str(s: str) -> str:
    """Normaliza un string: quita acentos, a minúsculas y espacios extra."""
    s = unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode('utf-8')
    return ' '.join(s.split())

# --------------------------------------------------------------------------------
# PLAYLISTS Y PODCASTS (Funciones originales sin cambios)
# --------------------------------------------------------------------------------
@handle_spotify_errors()
def get_podcast_episodes(sp: Spotify, podcast_id: str) -> List[str]:
    """Devuelve URIs de TODOS los episodios de un podcast (maneja paginación)."""
    episodes, offset, limit = [], 0, 50
    while True:
        resp = sp.show_episodes(podcast_id, limit=limit, offset=offset)
        items = resp.get("items", [])
        if not items:
            break
        episodes.extend(
            [f"spotify:episode:{ep['id']}" for ep in items if ep and ep.get("id")]
        )
        offset += len(items)
        if offset >= resp.get("total", 0):
            break
    return episodes

@handle_spotify_errors()
def get_playlist_items(sp: Spotify, playlist_id: str) -> Optional[List[str]]:
    """Devuelve URIs (track o episode) que ya existen en la playlist."""
    items, offset = [], 0
    while True:
        resp = read_items(sp, playlist_id, limit=100, offset=offset)
        batch = resp.get("items", [])
        if not batch:
            break
        for it in batch:
            track = it.get("track")
            if track and track.get("uri"):
                items.append(track["uri"])
        offset += len(batch)
        if not resp.get("next"):
            break
    return items

@handle_spotify_errors()
def add_episodes_to_playlist(sp: Spotify, playlist_id: str, episode_uris: List[str]) -> None:
    """Agrega episodios evitando duplicados."""
    existentes_uris = get_playlist_items(sp, playlist_id)
    if existentes_uris is None:
        return

    existentes: Set[str] = set(existentes_uris)
    nuevos = [uri for uri in episode_uris if uri not in existentes]
    
    if not nuevos:
        logger.info("No hay episodios nuevos para agregar.")
        return

    for i in range(0, len(nuevos), 100):
        add_items(sp, playlist_id, nuevos[i:i + 100])
    
    logger.info("Agregados %s episodios nuevos a %s", len(nuevos), playlist_id)

@handle_spotify_errors()
def obtener_playlists_usuario(sp: Spotify) -> List[Tuple[str, str, int]]:
    """[(playlist_id, nombre, total_tracks)…]"""
    playlists, offset = [], 0
    while True:
        res = sp.current_user_playlists(limit=50, offset=offset)
        playlists += [
            (it["id"], it["name"], (it.get("items") or it.get("tracks") or {}).get("total", 0))
            for it in res.get("items", [])
        ]
        if not res.get("next"):
            break
        offset += 50
    return playlists

@handle_spotify_errors()
def crear_playlist(sp: Spotify, nombre_playlist: str, public: bool = False) -> str:
    nueva = create_playlist(sp, nombre_playlist, public=public)
    return nueva["id"]

@handle_spotify_errors()
def eliminar_items_playlist(sp: Spotify, playlist_id: str, uris: List[str]) -> None:
    remove_items(sp, playlist_id, [{"uri": uri} for uri in uris])
    logger.info("Eliminados %s items de %s", len(uris), playlist_id)

@handle_spotify_errors()
def obtener_contenido_playlist(
    sp: Spotify, playlist_id: str
) -> List[Tuple[str, str, str]]:
    """[(track_id, nombre, artista/show)]"""
    contenido, offset = [], 0
    while True:
        resp = read_items(sp, playlist_id, limit=50, offset=offset)
        for it in resp.get("items", []):
            track = it.get("track")
            if not track:
                continue
            tid = track.get("id")
            nombre = track.get("name", "Desconocido")
            if track.get("type") == "episode":
                artista_show = track.get("show", {}).get("name", "Desconocido")
            else:
                artistas = track.get("artists", [])
                artista_show = ", ".join(a["name"] for a in artistas) if artistas else "Desconocido"
            contenido.append((tid, nombre, artista_show))
        if not resp.get("next"):
            break
        offset += len(resp.get("items", []))
    return contenido

@handle_spotify_errors()
def get_playlist_track_ids(sp: Spotify, playlist_id: str) -> Optional[Set[str]]:
    """Devuelve un set de IDs de las canciones en la playlist (OPTIMIZADO)."""
    track_ids = set()
    offset = 0
    while True:
        resp = read_items(sp, playlist_id, limit=100, offset=offset, fields="items(track(id)),next")
        items = resp.get("items", [])
        if not items:
            break
        for it in items:
            track = it.get("track")
            if track and track.get("id"):
                track_ids.add(track["id"])
        offset += len(items)
        if not resp.get("next"):
            break
    return track_ids

@handle_spotify_errors()
def obtener_artistas_seguidos(sp: Spotify):
    artistas = []
    datos = sp.current_user_followed_artists()
    while datos:
        for art in datos["artists"]["items"]:
            genero = (art.get("genres") or [""])[0]
            artistas.append((art["id"], art["name"], genero))
        if datos["artists"]["next"]:
            datos = sp.next(datos["artists"])
        else:
            break
    return artistas

@handle_spotify_errors()
def obtener_podcasts_guardados(sp: Spotify):
    podcasts = []
    datos = sp.current_user_saved_shows()
    while datos:
        for it in datos.get("items", []):
            show = it.get("show")
            if show:
                podcasts.append((show["id"], show["name"], show.get("publisher", "")))
        datos = sp.next(datos) if datos.get("next") else None
    return podcasts

# --------------------------------------------------------------------------------
# FUNCIONES DE ARTISTAS OPTIMIZADAS
# --------------------------------------------------------------------------------

def _get_all_pages(sp: Spotify, initial_results: dict) -> List[Dict]:
    """Función auxiliar para obtener todos los items de una respuesta paginada."""
    items = []
    if not initial_results:
        return items

    is_search = 'tracks' in initial_results
    results = initial_results.get('tracks', {}) if is_search else initial_results
    
    if results:
        items.extend(results.get('items', []))

    while results and results.get('next'):
        try:
            results = sp.next(results)
            if is_search:
                page_items = results.get('tracks', {}).get('items', [])
                results = results.get('tracks', {})
            else:
                page_items = results.get('items', [])
            items.extend(page_items)
        except Exception as e:
            logger.error(f"Error al obtener la siguiente página: {e}")
            break
    return items

# ############################################################################
# ##                INICIO DE LA FUNCIÓN MODIFICADA                         ##
# ############################################################################

@handle_spotify_errors()
def obtener_canciones_artista(sp: Spotify, artista_id: str) -> List[Dict]:
    """
    Obtiene TODAS las canciones de un artista, incluyendo colaboraciones,
    y filtra duplicados de forma inteligente, conservando versiones especiales.
    """
    try:
        artist_details = sp.artist(artista_id)
        artist_name = artist_details['name']
        logger.info(f"Iniciando búsqueda exhaustiva para: {artist_name}")
    except Exception as e:
        logger.error(f"Error obteniendo artista {artista_id}: {e}")
        raise

    # --- PASO 1: Recopilar TODAS las canciones de todas las fuentes ---
    
    all_tracks_raw: List[Dict] = []
    processed_album_ids: Set[str] = set()

    logger.info("1/3 - Obteniendo álbumes, sencillos y 'appears_on'...")
    for album_type in ['album', 'single', 'compilation', 'appears_on']:
        try:
            initial_albums = sp.artist_albums(artista_id, album_type=album_type, limit=50)
            all_albums = _get_all_pages(sp, initial_albums)
            
            album_ids_to_process = [
                album.get('id') for album in all_albums 
                if album and album.get('id') and album.get('id') not in processed_album_ids
            ]
            processed_album_ids.update(album_ids_to_process)

            for album_id in album_ids_to_process:
                initial_tracks = sp.album_tracks(album_id, limit=50)
                album_tracks = _get_all_pages(sp, initial_tracks)
                
                track_ids_to_fetch = [t['id'] for t in album_tracks if t and t.get('id')]
                
                for i in range(0, len(track_ids_to_fetch), 50):
                    batch_ids = track_ids_to_fetch[i:i+50]
                    if not batch_ids: continue
                    full_track_details = cached_entities(sp, "track", batch_ids)
                    all_tracks_raw.extend(t for t in full_track_details['tracks'] if t)
        except Exception as e:
            logger.warning(f"Error procesando {album_type} para {artist_name}: {e}")

    logger.info("2/3 - Obteniendo top tracks...")
    try:
        top_tracks = search_paginated(sp, f'artist:"{artist_name}"', 'track', 50)
        all_tracks_raw.extend(top_tracks.get('tracks', {}).get('items', []))
    except Exception as e:
        logger.warning(f"Error obteniendo top tracks: {e}")

    # ===== CAMBIO PRINCIPAL AQUÍ: BÚSQUEDA MÁS AGRESIVA =====
    logger.info("3/3 - Realizando múltiples búsquedas para encontrar todas las colaboraciones...")
    
    # Se usan varias consultas para capturar diferentes formas de créditos
    search_queries = [
        f'artist:"{artist_name}"',      # Búsqueda principal y más precisa
        f'"{artist_name}"',             # Búsqueda general del nombre como texto
        f'"feat. {artist_name}"',       # Búsqueda de "feat."
        f'"ft. {artist_name}"',         # Búsqueda de "ft."
        f'"con {artist_name}"',         # Búsqueda de "con" (común en español)
        f'"{artist_name} Remix"',       # Búsqueda de remixes hechos por el artista
    ]

    for query in search_queries:
        try:
            logger.info(f"    -> Buscando con query: {query}")
            initial_search = search_paginated(sp, query, 'track', 200)
            search_tracks = _get_all_pages(sp, initial_search)
            all_tracks_raw.extend(search_tracks)
            time.sleep(0.1) # Pequeña pausa para no saturar la API
        except Exception as e:
            logger.warning(f"Error en la búsqueda con query '{query}': {e}")
    
    # --- PASO 2: Filtrar y procesar los resultados ---
    logger.info(f"Procesando {len(all_tracks_raw)} tracks crudos encontrados...")

    unique_tracks_by_id: Dict[str, Dict] = {}
    for track in all_tracks_raw:
        if not track or not track.get('id'):
            continue
        
        artist_is_present = any(
            artist.get('id') == artista_id for artist in track.get('artists', [])
        )
        if artist_is_present and track['id'] not in unique_tracks_by_id:
            unique_tracks_by_id[track['id']] = track
    
    grouped_by_name = defaultdict(list)
    for track in unique_tracks_by_id.values():
        normalized_name = _normalize_str(track['name'])
        grouped_by_name[normalized_name].append(track)
    
    # --- PASO 3: Lógica de selección de versiones ---
    
    final_tracks: List[Dict] = []
    special_keywords = ['remix', 'live', 'acoustic', 'edit', 'version', 'remaster', 'instrumental', 'demo']

    for name, track_group in grouped_by_name.items():
        if len(track_group) == 1:
            final_tracks.append(track_group[0])
            continue

        track_group.sort(key=lambda t: (t.get('album', {}).get('release_date', ''), t.get('duration_ms', 0)), reverse=True)
        final_tracks.append(track_group[0])
        
        added_uris = {track_group[0]['uri']}
        for track in track_group[1:]:
            track_name_lower = track['name'].lower()
            if any(keyword in track_name_lower for keyword in special_keywords):
                if track['uri'] not in added_uris:
                    final_tracks.append(track)
                    added_uris.add(track['uri'])

    logger.info(f"RESULTADO FINAL: {len(final_tracks)} canciones únicas para {artist_name}")
    return final_tracks

# ############################################################################
# ##                  FIN DE LA FUNCIÓN MODIFICADA                          ##
# ############################################################################

@handle_spotify_errors()
def agregar_canciones_a_playlist(sp: Spotify, playlist_id: str, tracks: List[dict]):
    """Versión optimizada que usa IDs directamente para evitar duplicados."""
    if not tracks:
        return 0
        
    existing_track_ids = get_playlist_track_ids(sp, playlist_id)
    if existing_track_ids is None:
        return -1
    
    new_track_uris = list(dict.fromkeys([
        track['uri'] for track in tracks 
        if track and track.get('id') and track.get('uri') and track['id'] not in existing_track_ids
    ]))
    
    if not new_track_uris:
        logger.info("No hay canciones nuevas para agregar")
        return 0
    
    added_count = 0
    for i in range(0, len(new_track_uris), 100):
        batch = new_track_uris[i:i + 100]
        try:
            add_items(sp, playlist_id, batch)
            added_count += len(batch)
        except Exception as e:
            logger.error(f"Error agregando lote a la playlist: {e}")
            raise
    
    logger.info(f"Agregadas {added_count} canciones nuevas")
    return added_count

@handle_spotify_errors()
def buscar_artistas(sp: Spotify, query: str) -> List[Tuple[str, str]]:
    """Busca artistas por nombre."""
    if not query:
        return []
    results = sp.search(q=query, type='artist', limit=10)
    artistas = results.get('artists', {}).get('items', [])
    return [(a['id'], a['name']) for a in artistas]

@handle_spotify_errors()
def unfollow_playlist(sp: Spotify, playlist_id: str):
    """Unfollows a playlist."""
    remove_from_library(sp, [f"spotify:playlist:{playlist_id}"])
    logger.info(f"Unfollowed playlist {playlist_id}")
    return True

@handle_spotify_errors()
def replace_playlist_items(sp: Spotify, playlist_id: str, items: list):
    """Replaces all items in a playlist."""
    replace_items(sp, playlist_id, items)
    logger.info(f"Replaced items in playlist {playlist_id}")
    return True

# --------------------------------------------------------------------------------
# PLAYLIST CLEANING
# --------------------------------------------------------------------------------

@handle_spotify_errors()
def _legacy_remove_duplicates_from_playlist(sp: Spotify, playlist_id: str) -> Tuple[int, int]:
    # DEPRECATED: positions no aparece en el contrato actual de DELETE /items.
    """
    Elimina canciones duplicadas de una playlist.

    Compara las canciones por su ID. Si hay duplicados, conserva solo la primera
    aparición y elimina las demás.

    Args:
        sp (Spotify): Objeto cliente de Spotipy.
        playlist_id (str): ID de la playlist a limpiar.

    Returns:
        Tuple[int, int]: Una tupla con (número de duplicados eliminados, total de canciones restantes).
                         Devuelve (0, 0) si hay un error.
    """
    logger.info(f"Iniciando limpieza de duplicados para la playlist: {playlist_id}")

    try:
        # 1. Obtener todos los tracks de la playlist
        items = []
        offset = 0
        while True:
            resp = read_items(sp, playlist_id, limit=50, offset=offset, fields="items(item(id,uri)),next,snapshot_id")
            batch = resp.get("items", [])
            if not batch:
                break
            items.extend(batch)
            offset += len(batch)
            if not resp.get("next"):
                break
        
        if not items:
            logger.info("La playlist está vacía. No hay nada que limpiar.")
            return 0, 0

        # 2. Identificar duplicados
        seen_track_ids = set()
        duplicates_to_remove = []  # Lista de { "uri": "spotify:track:...", "positions": [index] }
        
        # Usamos un diccionario para agrupar posiciones por URI
        uri_positions = defaultdict(list)
        for i, item in enumerate(items):
            track = item.get("track")
            if track and track.get("uri"):
                uri_positions[track["uri"]].append(i)

        for uri, positions in uri_positions.items():
            if len(positions) > 1:
                # Hay duplicados. Conservamos la primera aparición, eliminamos el resto.
                for pos in positions[1:]:
                    duplicates_to_remove.append({"uri": uri, "positions": [pos]})

        if not duplicates_to_remove:
            logger.info("No se encontraron canciones duplicadas.")
            return 0, len(items)

        # 3. Eliminar los duplicados
        logger.info(f"Se encontraron {len(duplicates_to_remove)} canciones duplicadas. Eliminando...")
        
        # La API permite eliminar hasta 100 items por llamada.
        # El formato es una lista de tracks, donde cada track es un diccionario con el URI y las posiciones.
        # Agrupamos las eliminaciones para ser más eficientes.
        
        # Creamos un diccionario para agrupar posiciones por URI para la eliminación
        tracks_to_remove_payload = defaultdict(list)
        for dup in duplicates_to_remove:
            tracks_to_remove_payload[dup['uri']].extend(dup['positions'])

        # Convertimos al formato final que espera la API
        final_payload = [{"uri": uri, "positions": sorted(positions)} for uri, positions in tracks_to_remove_payload.items()]

        removed_count = 0
        for i in range(0, len(final_payload), 100):
            batch = final_payload[i:i+100]
            remove_items(sp, playlist_id, batch)
            removed_count += sum(len(item['positions']) for item in batch)

        total_remaining = len(items) - removed_count
        logger.info(f"Limpieza completada. Se eliminaron {removed_count} duplicados. Quedan {total_remaining} canciones.")
        
        return removed_count, total_remaining

    except Exception as e:
        logger.error(f"Error durante la limpieza de duplicados de la playlist {playlist_id}: {e}")
        raise

# --------------------------------------------------------------------------------
def remove_duplicates_from_playlist(sp: Spotify, playlist_id: str) -> Tuple[int, int]:
    from .spotify_compat import clean_duplicates
    return clean_duplicates(sp, playlist_id)

# API STATUS
# --------------------------------------------------------------------------------

def check_spotify_api_status() -> Tuple[str, str]:
    """Verifica el estado de la API de Spotify."""
    try:
        response = requests.get("https://status.spotify.dev/api/v2/status.json", timeout=5)
        response.raise_for_status()
        data = response.json()
        indicator = data.get("status", {}).get("indicator", "unknown")
        description = data.get("status", {}).get("description", "Could not determine status")
        return indicator, description
    except requests.exceptions.RequestException:
        try:
            requests.head("https://api.spotify.com", timeout=5)
            return "none", "All Systems Operational (fallback check)"
        except requests.exceptions.RequestException as e2:
            if "Failed to resolve" in str(e2):
                return "error", "Could not resolve Spotify domains. Check internet connection."
            else:
                return "error", "Could not connect to Spotify API. Service may be unavailable."

# --------------------------------------------------------------------------------
# FUNCIONES PARA ARTIST_MANAGER.PY (y otras partes del proyecto)
# --------------------------------------------------------------------------------

@handle_spotify_errors()
def get_current_user(sp: Spotify):
    """Gets the current user's profile."""
    return sp.current_user()

@handle_spotify_errors()
def search(sp: Spotify, q: str, type: str, limit: int):
    """Performs a search."""
    return search_paginated(sp, q, type, limit)

@handle_spotify_errors()
def user_playlist_create(sp: Spotify, user: str, name: str, public: bool, description: str):
    """Creates a playlist."""
    return create_playlist(sp, name, public=public, description=description)

@handle_spotify_errors()
def playlist_add_items(sp: Spotify, playlist_id: str, items: list):
    """Adds items to a playlist."""
    return add_items(sp, playlist_id, items)

@handle_spotify_errors()
def current_user_playlists(sp: Spotify, limit: int = 50, offset: int = 0):
    """Gets the current user's playlists."""
    return sp.current_user_playlists(limit=limit, offset=offset)

@handle_spotify_errors()
def playlist_items(sp: Spotify, playlist_id: str, fields: Optional[str] = None, limit: int = 100, offset: int = 0):
    """Gets items from a playlist."""
    return read_items(sp, playlist_id, fields=fields, limit=limit, offset=offset)

@handle_spotify_errors()
def next_page(sp: Spotify, result: dict):
    """Gets the next page of results from a paginated response."""
    if result and result.get('next'):
        return sp.next(result)
    return None

@handle_spotify_errors()
def recommendations(sp: Spotify, seed_genres: list, limit: int, country: str = "US", **kwargs):
    """Get recommendations based on seed genres."""
    # DEPRECATED: endpoint no disponible en Modo Desarrollo.
    raise NotImplementedError("Usa ai_recommender")

@handle_spotify_errors()
def show(sp: Spotify, show_id: str, market: str):
    """Get information about a single show."""
    return sp.show(show_id, market=market)

@handle_spotify_errors()
def playlist(sp: Spotify, playlist_id: str, fields: Optional[str] = None):
    """Get a playlist."""
    return sp.playlist(playlist_id, fields=fields)

@handle_spotify_errors()
def artists(sp: Spotify, artist_ids: list):
    """Get information about several artists."""
    return cached_entities(sp, "artist", artist_ids)

@handle_spotify_errors()
def tracks(sp: Spotify, track_ids: list):
    """Get information about several tracks."""
    return cached_entities(sp, "track", track_ids)

@handle_spotify_errors()
def artist_albums(sp: Spotify, artist_id: str, album_type: Optional[str] = None, country: Optional[str] = None, limit: int = 20, offset: int = 0):
    """Get an artist's albums."""
    return sp.artist_albums(artist_id, album_type=album_type, country=country, limit=limit, offset=offset)

@handle_spotify_errors()
def album_tracks(sp: Spotify, album_id: str, limit: int = 50, offset: int = 0):
    """Get an album's tracks."""
    return sp.album_tracks(album_id, limit=limit, offset=offset)
