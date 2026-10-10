# src/gui/podcasts.py

"""
Ventana para sincronizar podcasts con sus playlists (data_podcasts).
"""

import tkinter as tk
from tkinter import ttk, messagebox
from spotipy import Spotify
import threading
from ..utils.spotify_utils import (
    get_podcast_episodes,
    get_playlist_items,
    add_episodes_to_playlist,
    show,
    playlist,
)
from ..data_podcasts import data_podcasts

# DEPRECATED: se conserva la implementaci?n original; usa la vista moderna.
def _legacy_ventana_sincronizar_podcasts_data(parent: ttk.Frame, sp: Spotify) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=20)
    frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text="Sincronizando podcasts con sus playlists…", font=("Arial", 11)).pack(pady=8)
    prog = ttk.Progressbar(frame, orient="horizontal", length=460, mode="determinate", maximum=len(data_podcasts) if data_podcasts else 1)
    prog.pack(pady=5, fill=tk.X, expand=True)
    lbl_estado = ttk.Label(frame, text="Esperando…", anchor="w")
    lbl_estado.pack(fill=tk.X, padx=10)
    txt_log = tk.Text(frame, height=10, wrap=tk.WORD, bg="#2a2a2a", fg="white", relief="flat")
    txt_log.pack(padx=10, pady=6, fill=tk.BOTH, expand=True)

    def log(msg: str):
        frame.after(0, lambda: (
            txt_log.insert(tk.END, msg + "\n"),
            txt_log.see(tk.END)
        ))

    def update_progress(idx, total, podcast_name, playlist_name):
        frame.after(0, lambda: (
            lbl_estado.config(text=f"{idx}/{total}  {podcast_name} → {playlist_name}"),
            prog.config(value=idx)
        ))

    def _sincronizar_thread():
        if not data_podcasts:
            log("No hay podcasts configurados en data_podcasts.py")
            return

        total = len(data_podcasts)
        
        for idx, pair in enumerate(data_podcasts, start=1):
            pod_id, pl_id = pair["podcast"], pair["playlist"]

            show_info = show(sp, pod_id, market="US")
            podcast_name = show_info["name"] if show_info else f"Podcast {pod_id[:8]}…"
            
            pl_info = playlist(sp, pl_id, fields="name")
            playlist_name = pl_info["name"] if pl_info else f"Playlist {pl_id[:8]}…"

            update_progress(idx, total, podcast_name, playlist_name)

            eps = get_podcast_episodes(sp, pod_id)
            if not eps:
                log(f"❌ {podcast_name}: sin episodios o error.")
                continue

            playlist_items_before = get_playlist_items(sp, pl_id)
            if playlist_items_before is None:
                log(f"❌ {podcast_name}: No se pudo obtener los items de la playlist {playlist_name}.")
                continue
            
            antes = set(playlist_items_before)
            add_episodes_to_playlist(sp, pl_id, eps)
            
            playlist_items_after = get_playlist_items(sp, pl_id)
            if playlist_items_after is None:
                log(f"❌ {podcast_name}: No se pudo verificar los items de la playlist {playlist_name} después de agregar.")
                continue

            despues = set(playlist_items_after)
            nuevos = len(despues) - len(antes)
            if nuevos:
                log(f"✅ {podcast_name}: {nuevos} nuevos → {playlist_name}")
            else:
                log(f"• {podcast_name}: 0 nuevos")
        
        frame.after(0, lambda: (
            lbl_estado.config(text="¡Sincronización completa!"),
            messagebox.showinfo("Terminado", "Todos los podcasts han sido sincronizados."),
            btn_sinc.config(state="normal")
        ))

    def sincronizar():
        btn_sinc.config(state="disabled")
        thread = threading.Thread(target=_sincronizar_thread)
        thread.daemon = True
        thread.start()

    btn_sinc = ttk.Button(frame, text="Iniciar sincronización", command=sincronizar)
    btn_sinc.pack(pady=10)
    return frame

def ventana_sincronizar_podcasts_data(parent, sp):
    from .modern_assignments import assignments_view
    return assignments_view(parent, sp, kind="podcast", sync_only=True)
