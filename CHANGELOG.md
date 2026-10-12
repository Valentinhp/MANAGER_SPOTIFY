# Registro de cambios

## Actualización modularizada — octubre de 2026

Esta actualización se prepara sobre la versión que ya estaba publicada en `master`. No reemplaza las credenciales ni los datos locales de cada instalación.

### IA y playlists

- Añade una navegación específica para las secciones de inicio, playlists, IA, exploración y sincronizaciones.
- Permite seleccionar una playlist propia como referencia desde **Radio de Ánimo** y **Chat musical**.
- Lee todas las canciones accesibles de la playlist y envía a la IA una muestra equilibrada de hasta 100 canciones.
- Usa la playlist completa como conjunto para calcular una aproximación general de estilo, sentimiento, feeling, energía, ritmo, época, idiomas y artistas recurrentes.
- Excluye las canciones originales y las sugerencias anteriores, muestra el estado de coincidencia y permite revisar antes de crear la playlist.
- Mantiene la creación de playlists separada de la generación: solo se escribe en Spotify al pulsar **Crear playlist**.

### Spotify

- Actualiza la creación de playlists para usar `POST /me/playlists`.
- Envía explícitamente `collaborative: false` junto con nombre, visibilidad y descripción.
- Valida localmente nombre obligatorio, nombre de hasta 100 caracteres y descripción de hasta 300 caracteres.
- Añade control de rate limits con persistencia de `Retry-After`, sin repetir lotes que Spotify ya confirmó.
- Mejora la lectura paginada de playlists y la compatibilidad entre respuestas antiguas y actuales de Spotipy.

### Interfaz y sincronización

- Añade biblioteca visual con portadas, miniaturas, duración y apertura de playlists.
- Mejora el progreso de búsquedas, IA, sincronizaciones de artistas, podcasts y operaciones de playlists.
- Muestra nombres reales de playlists en asignaciones, historial y resultados.
- Conserva las pantallas existentes dentro de la nueva navegación.

### Seguridad y distribución

- `.env`, `.cache`, tokens, datos locales, logs, builds y entornos virtuales no forman parte de la actualización.
- El ejecutable sigue requiriendo un `.env` separado; las credenciales no se empaquetan.
- Si un Client Secret fue expuesto en versiones anteriores, debe regenerarse en Spotify y revocarse el token OAuth local.

### Validación realizada

- Suite completa: `61 passed`.
- Smoke test de GUI: `24 pantallas abiertas sin red real ni errores de Tk`.
- Pruebas específicas para paginación de playlists, exclusión de canciones, creación de playlists, rate limits y respuestas compatibles de Spotify.

## Publicación

Desde la raíz del repositorio:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m tests.smoke_gui
git diff --check
git status --short
git checkout modularizado
git add -A
git diff --cached --check
git commit -m "Publicar actualización modularizada"
git push -u origin modularizado
```

Luego crea un Pull Request de `modularizado` a `master`. Antes de confirmar el commit, revisa que no aparezcan `.env`, `.cache`, `data/`, `logs/`, `build/`, `dist/` ni `.venv/` en `git status`.
