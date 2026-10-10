import hashlib
import io
import requests
from PIL import Image
from ..config import CACHE_DIR

def load_cover(url):
    if not url:
        return None
    directory = CACHE_DIR / 'covers'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(url.encode()).hexdigest()+'.png')
    if path.exists():
        with Image.open(path) as cached:
            return cached.copy()
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as source:
        image = source.convert('RGB')
        image.thumbnail((180, 180))
        image.save(path)
        return image
