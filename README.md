# 🎧 SPOTYVMANAGER (Versión Modularizada)

Este proyecto es una aplicación de escritorio en Python que te ayuda a gestionar tu cuenta de Spotify de forma más avanzada y automatizada. Usa `Spotipy` y `Tkinter` para tener una interfaz fácil de usar.

---

## 🧩 ¿Qué hace esta app?

- Ver tus playlists
- Crear nuevas playlists
- Vaciar/eliminar playlists
- Obtener el top de canciones
- Sincronizar episodios de podcasts con playlists
- Buscar artistas y generar playlists automáticas con sus canciones
- Usar funciones avanzadas como búsqueda personalizada o filtrado por popularidad

---

## 📁 Estructura de carpetas
SPOTYVMANAGER/
│
├── src/
│ ├── main.py # Punto de entrada principal
│ ├── auth.py # Autenticación con Spotify
│ ├── ui/
│ │ ├── main_window.py # Menú principal
│ │ ├── playlists.py # Ventanas de gestión de playlists
│ │ ├── podcasts.py # Ventana de sincronización de podcasts
│ │ ├── artist_manager.py # Ventana de gestor automático
│ │ ├── search_advanced.py # Ventana de búsqueda avanzada
│ │ └── top_tracks.py # Ventana de top de canciones
│
├── .env
├── requirements.txt # Dependencias
└── README.md # Este archivo
