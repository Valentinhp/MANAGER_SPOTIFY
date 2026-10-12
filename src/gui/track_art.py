"""Load a bounded batch of tree thumbnails outside the Tk thread."""
from PIL import ImageTk
from .async_tasks import run_job
from .visual_library import image_url
from ..utils.covers import load_cover


def load_tree_art(frame, tree, tracks):
    token = getattr(tree, 'art_token', 0) + 1
    tree.art_token = token
    tree.art_images = []
    def work():
        images = []
        for key, track in tracks[:40]:
            try:
                value = load_cover(image_url(track or {}))
                if value:
                    images.append((key, value.resize((40, 40))))
            except Exception:
                pass
        return images
    def loaded(images):
        if token != tree.art_token:
            return
        for key, value in images:
            if tree.exists(key):
                photo = ImageTk.PhotoImage(value, master=tree)
                tree.art_images.append(photo)
                tree.item(key, image=photo)
    run_job(frame, work, loaded, on_error=lambda _: None)
