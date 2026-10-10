import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from ..config import DATA_DIR

HISTORY_FILE = DATA_DIR / 'ai_history.json'
_lock = threading.RLock()

def load_history():
    with _lock:
        if not HISTORY_FILE.exists():
            return []
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
            if not isinstance(data, list):
                raise ValueError('El historial debe ser una lista')
            return data
        except (ValueError, OSError) as error:
            logging.warning('No se pudo leer el historial local: %s', error)
            raise RuntimeError('El historial local está dañado o no se puede leer. Consérvalo como respaldo antes de repararlo.') from error

def _write(rows):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = HISTORY_FILE.with_suffix('.tmp')
    temporary.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(HISTORY_FILE)

def save_generation(prompt, songs):
    entry = {'id': str(uuid.uuid4()), 'date': datetime.now().astimezone().isoformat(),
        'prompt': prompt, 'songs': songs, 'playlist_id': None}
    with _lock:
        rows = load_history()
        rows.append(entry)
        _write(rows)
    return entry['id']

def attach_playlist(entry_id, playlist_id):
    with _lock:
        rows = load_history()
        for entry in rows:
            if entry['id'] == entry_id:
                entry['playlist_id'] = playlist_id
                _write(rows)
                return
        raise ValueError('No se encontró la generación en el historial.')
