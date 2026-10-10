# src/gui/artist_manager.py
"""
VentanaGestorAutomático: busca un artista, obtiene sus canciones únicas y gestiona playlists.
Interfaz pulida: tema oscuro, estilo Spotify, grid adaptable y componentes refinados.
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from spotipy import Spotify
import time
from ..utils.spotify_utils import (
    obtener_canciones_artista,
    get_current_user,
    search,
    user_playlist_create,
    playlist_add_items,
    current_user_playlists,
    playlist_items,
    next_page,
)

# DEPRECATED: vista original conservada.
class _LegacyVentanaGestorAutomatico(ttk.Frame):
    def __init__(self, parent: ttk.Frame, sp: Spotify, **kwargs):
        super().__init__(parent, **kwargs)
        self.sp = sp

        user = get_current_user(self.sp)
        if not user:
            messagebox.showerror("Error de Autenticación", "No se pudo obtener la información del usuario.")
            self.destroy()
            return
        self.user_id = user["id"]

        self.artists_found: list[dict] = []
        self.songs: list[dict] = []
        self.playlists: list[dict] = []
        self.artist_id: str = ""

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#191414")
        style.configure("Header.TLabel", background="#191414", foreground="#1DB954", font=("Segoe UI", 14, "bold"))
        style.configure("TLabel", background="#191414", foreground="#FFFFFF", font=("Segoe UI", 10))
        style.configure("TButton", background="#1DB954", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"), padding=6)
        style.map("TButton", background=[("active", "#1ed760")])
        style.configure("TEntry", fieldbackground="#2a2a2a", foreground="#FFFFFF", padding=4)
        style.configure("TRadiobutton", background="#191414", foreground="#FFFFFF", font=("Segoe UI", 10))

        self._crear_widgets()

    def _crear_widgets(self):
        main = ttk.Frame(self, style="TFrame", padding=15)
        main.pack(expand=True, fill=tk.BOTH)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1) # Fila de la lista de canciones

        # 1) Búsqueda de artista
        ttk.Label(main, text="1) Buscar artista", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 5))
        busc = ttk.Frame(main, style="TFrame")
        busc.grid(row=1, column=0, sticky="ew", pady=5)
        busc.columnconfigure(0, weight=1)
        self.entry_artist = ttk.Entry(busc, style="TEntry")
        self.entry_artist.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(busc, text="Buscar", command=self.search_artist).grid(row=0, column=1)

        self.lb_artists = tk.Listbox(main, bg="#2a2a2a", fg="white", selectbackground="#1DB954", height=6, bd=0)
        self.lb_artists.grid(row=2, column=0, sticky="nsew", pady=5)
        sb_art = ttk.Scrollbar(main, orient="vertical", command=self.lb_artists.yview)
        sb_art.grid(row=2, column=1, sticky="ns")
        self.lb_artists.config(yscrollcommand=sb_art.set)
        self.lb_artists.bind("<<ListboxSelect>>", self.on_artist_select)

        # 2) Informe de canciones (Recuperado del código original)
        rpt = ttk.LabelFrame(main, text="Resumen de canciones", padding=8)
        rpt.grid(row=3, column=0, columnspan=2, sticky="ew", pady=10)
        rpt.columnconfigure(0, weight=1)
        self.lbl_report = ttk.Label(rpt, text="No hay datos aún.", style="TLabel")
        self.lbl_report.grid(row=0, column=0, sticky="w")

        # 3) Lista de canciones únicas
        songs_f = ttk.LabelFrame(main, text="Canciones únicas encontradas", padding=8)
        songs_f.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=5)
        songs_f.columnconfigure(0, weight=1)
        songs_f.rowconfigure(0, weight=1)
        self.tree_songs = ttk.Treeview(songs_f, columns=("Name",), show="headings", selectmode="none", height=8)
        self.tree_songs.heading("Name", text="Título de canción")
        self.tree_songs.column("Name", anchor="w")
        self.tree_songs.grid(row=0, column=0, sticky="nsew")
        sb_songs = ttk.Scrollbar(songs_f, orient="vertical", command=self.tree_songs.yview)
        sb_songs.grid(row=0, column=1, sticky="ns")
        self.tree_songs.configure(yscrollcommand=sb_songs.set)

        # 4) Generar o actualizar playlist
        play_f = ttk.LabelFrame(main, text="Generar o actualizar playlist", padding=8)
        play_f.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        play_f.columnconfigure(1, weight=1)
        self.play_var = tk.StringVar(value="nueva")
        ttk.Radiobutton(play_f, text="Crear nueva", variable=self.play_var, value="nueva", command=self.update_play_option).grid(row=0, column=0, padx=(0, 10))
        ttk.Radiobutton(play_f, text="Usar existente", variable=self.play_var, value="existente", command=self.update_play_option).grid(row=0, column=1)

        self.dynamic = ttk.Frame(play_f, style="TFrame")
        self.dynamic.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        self.update_play_option()

        # Botón de Reset
        ttk.Button(main, text="Reset", command=self.reset_to_artist_search).grid(row=6, column=0, sticky="e", pady=(10, 0))

    def search_artist(self):
        q = self.entry_artist.get().strip()
        if not q:
            messagebox.showinfo("Info", "Ingresa un nombre.")
            return
        
        res = search(self.sp, q=q, type="artist", limit=10)
        if res and "artists" in res and "items" in res["artists"]:
            self.artists_found = res["artists"]["items"]
            self.lb_artists.delete(0, tk.END)
            for art in self.artists_found:
                self.lb_artists.insert(tk.END, art["name"])
        else:
            messagebox.showerror("Error", "Error al buscar artista.")
            self.artists_found = []
            self.lb_artists.delete(0, tk.END)


    def on_artist_select(self, _evt):
        sel = self.lb_artists.curselection()
        if not sel: return
        art = self.artists_found[sel[0]]
        if messagebox.askyesno("Confirmar", f"Seleccionaste {art['name']}. ¿Obtener todas sus canciones? (Puede tardar)"):
            self.artist_id = art["id"]
            self.fetch_artist_songs()

    def fetch_artist_songs(self):
        self.songs = obtener_canciones_artista(self.sp, self.artist_id)
        if self.songs is None:
            messagebox.showerror("Error", "Ocurrió un error al obtener las canciones (posiblemente un timeout o error de API).")
            self.songs = []

        messagebox.showinfo("Info", f"Se encontraron {len(self.songs)} canciones únicas.")
        
        self.tree_songs.delete(*self.tree_songs.get_children())
        
        sorted_songs = sorted(self.songs, key=lambda s: s.get('name', ''))
        for s in sorted_songs:
            self.tree_songs.insert("", "end", values=(s["name"],))
        
        self.lbl_report.config(text=f"Total únicas: {len(self.songs)}")

    def update_play_option(self):
        for w in self.dynamic.winfo_children(): w.destroy()
        if self.play_var.get() == "nueva":
            ttk.Label(self.dynamic, text="Nombre playlist:").grid(row=0, column=0, sticky="w")
            self.new_name = ttk.Entry(self.dynamic, style="TEntry")
            self.new_name.grid(row=0, column=1, sticky="ew", padx=(5, 0))
            ttk.Button(self.dynamic, text="Crear & Agregar", command=self.crear_playlist_y_agregar_songs).grid(row=1, column=0, columnspan=2, pady=5)
        else:
            ttk.Label(self.dynamic, text="Buscar playlist:").grid(row=0, column=0, sticky="w")
            self.search_pl = ttk.Entry(self.dynamic, style="TEntry")
            self.search_pl.grid(row=0, column=1, sticky="ew", padx=(5, 0))
            self.search_pl.bind("<KeyRelease>", self.filtrar_playlists)
            self.pl_list = tk.Listbox(self.dynamic, bg="#2a2a2a", fg="white", selectbackground="#1DB954", height=4, bd=0)
            self.pl_list.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
            self.load_all_playlists()
            ttk.Button(self.dynamic, text="Actualizar", command=self.actualizar_playlist_seleccionada).grid(row=2, column=0, columnspan=2, pady=5)

    def crear_playlist_y_agregar_songs(self):
        name = self.new_name.get().strip()
        if not name:
            messagebox.showinfo("Info", "Ingresa nombre.")
            return
        if not self.songs:
            messagebox.showinfo("Info", "No hay canciones para agregar.")
            return

        pl = user_playlist_create(self.sp, self.user_id, name, public=True, description="Playlist generada automáticamente")
        if not pl:
            messagebox.showerror("Error", "No se pudo crear la playlist.")
            return

        ids = [s["id"] for s in self.songs]
        for i in range(0, len(ids), 100):
            if not playlist_add_items(self.sp, pl["id"], ids[i:i + 100]):
                messagebox.showerror("Error", f"No se pudieron agregar algunas canciones a la playlist.")
                return
            time.sleep(0.2)
        messagebox.showinfo("Listo", "Playlist creada y canciones agregadas.")

    def load_all_playlists(self):
        self.playlists.clear()
        self.pl_list.delete(0, tk.END)
        res = current_user_playlists(self.sp, limit=50)
        while res:
            for p in res["items"]:
                self.playlists.append(p)
                self.pl_list.insert(tk.END, p["name"])
            res = next_page(self.sp, res) if res.get("next") else None

    def filtrar_playlists(self, _evt):
        term = self.search_pl.get().strip().lower()
        self.pl_list.delete(0, tk.END)
        for p in self.playlists:
            if term in p["name"].lower(): self.pl_list.insert(tk.END, p["name"])

    def actualizar_playlist_seleccionada(self):
        sel = self.pl_list.curselection()
        if not sel:
            messagebox.showinfo("Info", "Selecciona playlist.")
            return
        if not self.songs:
            messagebox.showinfo("Info", "No hay canciones para agregar.")
            return

        selected_name = self.pl_list.get(sel[0])
        pl_id = None
        for p in self.playlists:
            if p["name"] == selected_name:
                pl_id = p["id"]
                break
        if not pl_id:
            messagebox.showerror("Error", "No se encontró el ID de la playlist.")
            return

        existentes = set()
        res = playlist_items(self.sp, pl_id, fields='items(track(id)),next')
        while res:
            existentes.update({item["track"]["id"] for item in res["items"] if item and item.get("track") and item["track"].get("id")})
            res = next_page(self.sp, res) if res.get("next") else None
        
        pendientes = [s["id"] for s in self.songs if s["id"] not in existentes]
        if not pendientes:
            messagebox.showinfo("Info", "No hay canciones nuevas que agregar.")
            return

        for i in range(0, len(pendientes), 100):
            if not playlist_add_items(self.sp, pl_id, pendientes[i:i + 100]):
                messagebox.showerror("Error", f"No se pudieron agregar algunas canciones a la playlist.")
                return
            time.sleep(0.2)
        messagebox.showinfo("Listo", f"Playlist actualizada con {len(pendientes)} canciones nuevas.")

    def reset_to_artist_search(self):
        self.songs.clear()
        self.artists_found.clear()
        self.lb_artists.delete(0, tk.END)
        self.tree_songs.delete(*self.tree_songs.get_children())
        self.lbl_report.config(text="No hay datos aún.")
        self.entry_artist.delete(0, tk.END)
        self.play_var.set("nueva")
        self.update_play_option()

def VentanaGestorAutomatico(parent, sp, **kwargs):
    from .modern_search import ventana_artistas
    return ventana_artistas(parent, sp)
