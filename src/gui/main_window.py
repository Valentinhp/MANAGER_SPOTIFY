"""
Ventana principal de SpotyVManager con estilo Spotify,
minimalista, suave y muy agradable.
"""

import tkinter as tk
from tkinter import Menu, ttk
from spotipy import Spotify
import threading

# Importa tus ventanas y funciones
from .playlists import (
    ventana_vaciar_playlists,
    ventana_eliminar_playlists,
    ventana_ver_playlists,
    ventana_crear_playlist,
)
from .podcasts import ventana_sincronizar_podcasts_data
from .artist_manager import VentanaGestorAutomatico
from .artistapy import ventana_artistapy
from .search_advanced import ventana_busqueda_avanzada
from .top_tracks import ventana_top_tracks
from .admin_podcasts import VentanaAdminPodcasts
from .assign_artist import ventana_asignar_artista_playlist
from .manage_assignments import VentanaGestionarAsignaciones
from .sync_assignments import VentanaSincronizarAsignaciones
from .log_viewer import ventana_log_viewer
from ..utils.spotify_utils import check_spotify_api_status

# Variable global para mantener la referencia al frame actual
current_frame = None

def build_main_window(sp: Spotify) -> tk.Tk:
    root = tk.Tk()
    root.title("SpotyVManager 🎧")
    root.geometry("1000x720")
    root.configure(bg="#0f0f0f")

    style = ttk.Style()
    style.theme_use("clam")
    # Estilos generales
    style.configure("TButton", font=("Segoe UI", 11, "bold"), background="#1DB954", foreground="white", padding=12, borderwidth=0)
    style.map("TButton", background=[("active", "#1ed760")])
    style.configure("TLabel", background="#121212", foreground="#dddddd", font=("Segoe UI", 12))
    style.configure("Title.TLabel", background="#121212", foreground="white", font=("Segoe UI", 24, "bold"))
    style.configure("Sub.TLabel", background="#121212", foreground="#bbbbbb", font=("Segoe UI", 14))
    style.configure("Content.TFrame", background="#121212")
    # Estilo para el botón de refrescar
    style.configure("Refresh.TButton", font=("Segoe UI", 9), padding=5)


    # --- Frame principal de contenido ---
    content_frame = ttk.Frame(root, style="Content.TFrame")
    content_frame.pack(expand=True, fill=tk.BOTH)

    def show_frame(frame_factory, *args):
        global current_frame
        if current_frame:
            current_frame.destroy()
        
        current_frame = frame_factory(content_frame, sp, *args)
        current_frame.pack(expand=True, fill=tk.BOTH)

    menu_bar = Menu(root, tearoff=0, bg="#1a1a1a", fg="white", activebackground="#1DB954")
    root.config(menu=menu_bar)

    def new_menu():
        return Menu(menu_bar, tearoff=0, bg="#1a1a1a", fg="white", activebackground="#1DB954")

    # --- Menú ---
    m_play = new_menu()
    m_play.add_command(label="Ver", command=lambda: show_frame(ventana_ver_playlists))
    m_play.add_command(label="Crear", command=lambda: show_frame(ventana_crear_playlist))
    m_play.add_command(label="Vaciar", command=lambda: show_frame(ventana_vaciar_playlists))
    m_play.add_command(label="Eliminar", command=lambda: show_frame(ventana_eliminar_playlists))
    menu_bar.add_cascade(label="🎵 Playlists", menu=m_play)

    m_pod = new_menu()
    m_pod.add_command(label="Sincronizar", command=lambda: show_frame(ventana_sincronizar_podcasts_data))
    m_pod.add_command(label="Administrar", command=lambda: show_frame(VentanaAdminPodcasts))
    menu_bar.add_cascade(label="🎙️ Podcasts", menu=m_pod)

    m_art = new_menu()
    m_art.add_command(label="Asignar Artista a Playlist", command=lambda: show_frame(ventana_asignar_artista_playlist))
    m_art.add_command(label="Gestionar Asignaciones", command=lambda: show_frame(VentanaGestionarAsignaciones))
    m_art.add_command(label="Sincronizar Asignaciones", command=lambda: show_frame(VentanaSincronizarAsignaciones))
    m_art.add_separator()
    m_art.add_command(label="Gestor Automático", command=lambda: show_frame(VentanaGestorAutomatico))
    m_art.add_command(label="Artistapy", command=lambda: show_frame(ventana_artistapy))
    menu_bar.add_cascade(label="🎤 Artistas", menu=m_art)

    m_bus = new_menu()
    m_bus.add_command(label="Avanzada", command=lambda: show_frame(ventana_busqueda_avanzada))
    menu_bar.add_cascade(label="🔍 Buscar", menu=m_bus)

    menu_bar.add_command(label="📈 Top Tracks", command=lambda: show_frame(ventana_top_tracks))
    menu_bar.add_command(label="📋 Registro", command=lambda: show_frame(ventana_log_viewer))
    menu_bar.add_command(label="❌ Salir", command=root.destroy)

    # --- Pantalla de inicio ---
    def create_home_frame(parent, sp_instance):
        home_frame = ttk.Frame(parent, style="Content.TFrame", padding=40)
        
        ttk.Label(home_frame, text="SpotyVManager", style="Title.TLabel").pack(pady=(0, 10))
        ttk.Label(home_frame, text="Gestiona tu música como nunca antes", style="Sub.TLabel").pack(pady=(0, 30))

        features = [
            "🎵 Crear, ver, eliminar y vaciar playlists",
            "📈 Consultar tus Top Tracks",
            "🎙️ Sincronizar podcasts al instante",
            "✨ Recomendaciones con Artistapy",
            "🔍 Búsqueda por frase, título o artista",
            "🧩 Administrar Podcasts y Playlists personalizados",
        ]
        for feat in features:
            lbl = ttk.Label(home_frame, text=feat, background="#121212")
            lbl.pack(anchor="w", pady=4)

        btn1 = ttk.Button(home_frame, text="Ver Playlists", command=lambda: show_frame(ventana_ver_playlists))
        btn1.pack(pady=(30, 10), fill="x")
        btn2 = ttk.Button(home_frame, text="Ver Top Tracks", command=lambda: show_frame(ventana_top_tracks))
        btn2.pack(pady=10, fill="x")
        btn3 = ttk.Button(home_frame, text="Abrir Gestor Automático", command=lambda: show_frame(VentanaGestorAutomatico))
        btn3.pack(pady=10, fill="x")
        
        return home_frame

    # Mostrar la pantalla de inicio al arrancar
    show_frame(create_home_frame)

    # --- Barra de estado de la API ---
    status_bar = tk.Frame(root, bg="#181818")
    status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(1, 0), ipady=2)

    status_indicator = tk.Canvas(status_bar, width=12, height=12, bg="#181818", highlightthickness=0)
    status_indicator.pack(side=tk.LEFT, padx=(10, 5))
    status_light = status_indicator.create_oval(2, 2, 12, 12, fill="grey", outline="")

    status_label = tk.Label(status_bar, text="Checking API status...", bg="#181818", fg="#aaaaaa", font=("Segoe UI", 9))
    status_label.pack(side=tk.LEFT)

    def _update_status_ui(indicator, description):
        color_map = {
            "none": "#1DB954",      # Verde (Operacional)
            "minor": "#FFD700",     # Amarillo (Degradado)
            "major": "#FFA500",     # Naranja (Parcialmente fuera de servicio)
            "critical": "#FF4500",  # Rojo (Fuera de servicio)
            "error": "#808080",     # Gris (Error de conexión)
            "unknown": "#808080"    # Gris (Desconocido)
        }
        color = color_map.get(indicator, "#808080")
        
        status_indicator.itemconfig(status_light, fill=color)
        status_label.config(text=description)
        refresh_button.config(state=tk.NORMAL) # Habilitar botón de nuevo

    def _check_api_in_thread():
        try:
            indicator, description = check_spotify_api_status()
            # Programar la actualización de la UI en el hilo principal
            root.after(0, _update_status_ui, indicator, description)
        except Exception as e:
            # Asegurarse de que cualquier error se maneje y se muestre en la UI
            root.after(0, _update_status_ui, "error", f"Failed to check status: {e}")

    def refresh_status():
        status_label.config(text="Checking...")
        refresh_button.config(state=tk.DISABLED) # Deshabilitar mientras se actualiza
        # Iniciar la comprobación en un nuevo hilo para no bloquear la UI
        threading.Thread(target=_check_api_in_thread, daemon=True).start()

    refresh_button = ttk.Button(status_bar, text="🔄", style="Refresh.TButton", command=refresh_status)
    refresh_button.pack(side=tk.RIGHT, padx=10)

    # Comprobación inicial al arrancar
    refresh_status()

    return root
