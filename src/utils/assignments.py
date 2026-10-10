"""Persistencia JSON de asignaciones, fuera del código y del ejecutable."""
import json
import threading
from pathlib import Path
from ..config import DATA_DIR

_lock=threading.RLock()

def load_assignments(kind='artist'):
    path=DATA_DIR / ('artist_assignments.json' if kind=='artist' else 'podcast_assignments.json')
    with _lock:
        if path.exists():
            value=json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(value,list):raise ValueError('Las asignaciones deben ser una lista.')
            return value
        if kind=='artist':
            original=Path(__file__).resolve().parents[1] / 'data_assignments.json'
            rows=json.loads(original.read_text(encoding='utf-8')) if original.exists() else []
        else:
            from ..data_podcasts import data_podcasts
            rows=list(data_podcasts)
        save_assignments(rows,kind)
        return rows

def save_assignments(rows,kind='artist'):
    path=DATA_DIR / ('artist_assignments.json' if kind=='artist' else 'podcast_assignments.json')
    with _lock:
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        temporary.replace(path)
    return True
