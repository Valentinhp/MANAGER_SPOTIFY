# SpotyVManager

Aplicación de escritorio en Python y CustomTkinter para organizar playlists, podcasts y asignaciones de artistas. Incluye sugerencias musicales de OpenAI, vista previa y creación de playlists con Spotify. Proyecto independiente, no oficial de Spotify.

## Instalación local

Requiere Python 3.10 o posterior con Tkinter; validado en Windows con Python 3.13.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si ya tienes `.venv`, utiliza su Python. Para pruebas y empaquetado:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

En Linux/macOS usa `.venv/bin/python`; algunas distribuciones Linux requieren instalar el paquete del sistema `python3-tk`.

## Spotify y .env

1. Entra al [Developer Dashboard](https://developer.spotify.com/dashboard) y crea una aplicación con acceso a Web API. Cada persona que instale su propia copia debe crear su propio Client ID y Client Secret.
2. En Settings registra exactamente `http://127.0.0.1:5000/callback` y usa esa misma dirección en `.env`. Spotify exige una IP loopback explícita; `localhost` no está permitido. [Redirect URIs](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).
3. Copia `.env.example` a `.env` si todavía no tienes uno. Conserva tu archivo existente si ya contiene credenciales.
4. Completa `CLIENT_ID` y `CLIENT_SECRET`. Para IA deja `AI_PROVIDER=chatgpt`: no requiere `OPENAI_API_KEY`.
5. Abre Radio de Ánimo, Chat musical o Resumen de gusto, pulsa **Continue with ChatGPT** y permite usar tu plan en el navegador. Después selecciona un modelo disponible y genera automáticamente. El acceso depende de la elegibilidad de tu cuenta y sus límites. [Conexión oficial al plan](https://developers.openai.com/siwc/token-sharing-open-source).
6. En Users Management agrega los usuarios de prueba. En Modo Desarrollo el propietario de la app debe mantener Premium y hay hasta 5 usuarios autorizados; quienes no estén en la lista pueden autenticarse pero recibirán 403. [Quota modes](https://developer.spotify.com/documentation/web-api/concepts/quota-modes). La actualización de julio permite hasta 25 Client IDs por desarrollador y comparte cuotas por cuenta; el límite antiguo de un Client ID ya no es vigente. [Changelog de julio de 2026](https://developer.spotify.com/documentation/web-api/references/changes/july-2026).

```dotenv
CLIENT_ID=tu_client_id
CLIENT_SECRET=tu_nuevo_client_secret
REDIRECT_URI=http://127.0.0.1:5000/callback
AI_PROVIDER=chatgpt
```

```powershell
.venv\Scripts\python.exe -m src.app
```

Spotify abre el navegador para autorizar al realizar la primera operación que necesita autenticación. Reinicia la app después de editar `.env`. Si cambias Client ID o permisos, conserva como respaldo y elimina tu caché OAuth local para autorizar de nuevo.

## IA automática con tu plan de ChatGPT

El inicio de sesión oficial solicita permiso para usar tu plan; no accede al historial de tus conversaciones ni toma la sesión de Codex. La primera conexión se completa en el navegador. La app conserva la sesión, renueva los tokens y descubre los modelos permitidos para tu cuenta. **Opciones** permite añadir o cambiar cuentas, actualizar modelos, cerrar sesión y abrir el uso del plan. Los límites compartidos y por aplicación se administran en [ChatGPT → Uso](https://chatgpt.com/settings/usage).

Este modo envía las solicitudes mediante OAuth al endpoint público de Responses, con streaming y sin almacenamiento remoto de respuestas. Espera la confirmación de respuesta completa antes de utilizar canciones sugeridas. Si faltan permisos, tu cuenta no es elegible o alcanzas un límite, muestra el error; **no cambia automáticamente a la API de pago**. [Modelos e inferencia](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference), [limitaciones](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations).

La sesión está en `data/chatgpt-session.bin`, excluida de Git y del ejecutable. En Windows se cifra con DPAPI para tu usuario; en Unix se guarda con permisos `0600`. Cada registro mantiene su propia cuenta y cliente. Los tokens se renuevan bajo bloqueo entre procesos y se escriben de forma atómica. Al cerrar sesión se intenta revocar el acceso remoto; si no se confirma, la app indica cómo revocarlo desde ChatGPT.

El modo anterior de API sigue disponible solo si configuras explícitamente `AI_PROVIDER=openai`, `OPENAI_API_KEY` y `AI_MODEL` en `.env`. Ese modo tiene facturación separada del plan de ChatGPT.

**Seguridad:** `.env` y `.cache` estuvieron versionados. Regenera el Client Secret en Spotify, revoca tokens anteriores y actualiza `.env`. Quitarlos del índice no elimina las versiones del historial. No compartas estos archivos. La limpieza del historial con `git filter-repo` sería un trabajo separado que requiere coordinar las copias existentes; no se reescribió el historial.

## Funciones

- Playlists: consultar contenido, crear, vaciar, dejar de seguir y limpiar duplicados.
- Artistas: buscar, explorar discografía, filtrar colaboraciones y géneros, ordenar por nombre, fecha o duración; agregar resultados a una playlist nueva o existente.
- Podcasts: buscar y asignar podcasts a playlists; sincronizar episodios evitando duplicados.
- Asignaciones de artistas: administrar y sincronizar canciones nuevas.
- Radio de Ánimo: generar hasta 15 sugerencias, revisar título/artista y estado de coincidencia, excluir canciones con doble clic y crear solo al pulsar Crear playlist.
- IA: sugerir nombre y descripción, pedir otras 15 excluyendo sugerencias previas, ordenar con arco de energía y refinar mediante chat. El chat conserva las últimas 20 intervenciones para limitar el contexto.
- Hora/clima: preparar una solicitud con la hora del sistema y una descripción opcional del clima escrita por ti. No requiere otra API ni transmite ubicación.
- Historial local: consultar solicitudes, canciones sugeridas y la playlist creada.
- Resumen del gusto: OpenAI genera un perfil a partir de tu descripción escrita.
- Fusión: selecciona dos playlists propias, revisa su combinación y crea una tercera intercalada, sin duplicados.

La política de Spotify prohíbe tanto entrenar modelos como ingresar contenido de Spotify a modelos de IA. Por ello OpenAI recibe exclusivamente texto del usuario y sugerencias previas generadas por OpenAI: no recibe metadatos obtenidos de Spotify, portadas, historial de escucha ni playlists. La fusión se calcula localmente; el perfil utiliza tu descripción en lugar de analizar automáticamente tus artistas seguidos o Top Tracks. [Developer Policy, III.13–14](https://developer.spotify.com/policy).

## Compatibilidad de Spotify

Verificación documental realizada el 9 de octubre de 2026. El enlace general solicitado para cambios no respondió; se consultaron los changelogs mensuales y las referencias oficiales. Los contratos se probaron con mocks, sin realizar escrituras en tu cuenta.

| Uso | Implementación actual |
| --- | --- |
| Search | Lotes de hasta 10, paginados por offset |
| Crear playlist | `POST /me/playlists` |
| Leer/agregar/reemplazar/quitar items | `GET/POST/PUT/DELETE /playlists/{id}/items` |
| Dejar de seguir playlist | `DELETE /me/library`, con URI de playlist |
| Consultas múltiples de tracks/artistas | Consultas individuales con caché en memoria y pausa |
| Top tracks de artista | Discografía y búsqueda por artista; no se presenta como ranking de popularidad |
| Recommendations | Helper obsoleto conservado; indica usar `ai_recommender` |
| Campos ausentes | Acceso tolerante a campos opcionales; sin filtros activos de popularidad |

Los cambios de endpoints y campos de febrero afectan al Modo Desarrollo; las apps con Extended Quota tienen condiciones distintas. `external_ids` se mantuvo tras revertirse su eliminación; `genres` no aparece como campo de artista eliminado. Los contenidos de playlists solo están disponibles para listas propias o colaborativas. [Guía de migración](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide), [changelog de febrero](https://developer.spotify.com/documentation/web-api/references/changes/february-2026), [changelog de marzo](https://developer.spotify.com/documentation/web-api/references/changes/march-2026).

Recommendations, Related Artists y Audio Features ya tenían restricciones para nuevas aplicaciones y determinadas apps en desarrollo desde noviembre de 2024. No se emplean en las vistas activas. New Releases y las consultas múltiples tampoco se usan. [Anuncio oficial de 2024](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api).

La limpieza de duplicados conserva la primera aparici?n y el orden, compara snapshots y repone la secuencia mediante el contrato documentado de PUT /items. Si hay items locales o no disponibles, no modifica la lista para conservarlos. No depende del campo positions, que no aparece en el contrato actual de DELETE /items.

HTTP 429 respeta `Retry-After` en segundo plano y limita reintentos; 403 muestra un mensaje sobre Premium del propietario, lista de usuarios y permisos. Las búsquedas extensas pueden tardar y consumir cuota. Los botones de operaciones se desactivan durante su trabajo y el indicador inferior señala tareas activas.

## Datos locales y estructura

El código activo está en `src/`. Se consolidaron 39 asignaciones del directorio duplicado; sus respaldos están en `local_backups/`, excluido de Git. Los módulos de UI anteriores se conservan con `# DEPRECATED`; sus entradas públicas dirigen a las vistas modernas.

- `src/utils/spotify_compat.py`: contratos actuales y normalización de respuestas.
- `src/utils/ai_recommender.py` y `ai_playlist_builder.py`: OpenAI y matching de títulos/artistas, sin confundir sugerencias con resultados confirmados.
- `src/gui/async_tasks.py`: workers con `threading.Thread` y `queue.Queue`; todos los widgets se actualizan en el hilo de Tk.
- `src/gui/main_modern.py`, `modern_*.py` y `ai_*.py`: sidebar y pantallas.
- `data/`: asignaciones JSON e historial de IA. La primera ejecución de una vista de asignaciones migra los datos existentes de `src/` sin borrarlos.
- `cache/covers/`: portadas descargadas y redimensionadas. En la vista de IA, Abrir en Spotify enlaza al contenido correspondiente.
- `logs/app.log`: registro rotatorio, incluidas sugerencias no encontradas.

Estos datos, credenciales, cachés, `.venv` y respaldos quedan excluidos de Git. En el ejecutable, datos, caché y logs se guardan bajo `%LOCALAPPDATA%\SpotyVManager` en Windows; en otros sistemas, bajo `~/SpotyVManager`.

## Validación

```powershell
.venv\Scripts\python.exe -m compileall src
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m tests.smoke_gui
.venv\Scripts\python.exe -m src.app --smoke
```

La prueba de navegación abre 21 pantallas con respuestas simuladas y comprueba que las llamadas simuladas de red ocurren fuera del hilo de Tk. `--smoke` abre el inicio y cierra la ventana automáticamente, sin autenticar ni realizar peticiones reales. Las pruebas cubren JSON, retry, matching, duplicados, historial concurrente, endpoints, paginación y errores 403/429. La autenticación real y las respuestas de las cuentas deben comprobarse tras renovar credenciales.

## Ejecutable

Ejecuta `build.bat` en Windows o `sh build.sh` en Linux/macOS, después de instalar `requirements-dev.txt`. PyInstaller construye `--onefile --windowed` e incluye los recursos de CustomTkinter. Debes compilar en cada sistema de destino.

El resultado queda en `dist/SpotyVManager.exe` en Windows. Crea un `.env` separado junto al ejecutable: **no se incluye dentro del binario**. El build tampoco agrega `data/`, `.cache` ni `.venv` como archivos de datos. Puedes ejecutar `dist/SpotyVManager.exe --smoke` para comprobar el arranque sin credenciales. Despu?s del build en Windows, `.venv\Scripts\python.exe -m tests.verify_build` verifica que todos los m?dulos propios empaquetados coinciden con el c?digo fuente y que no hay archivos `.env` ni `.cache`. Los scripts usan `--clean` para evitar reutilizar m?dulos obsoletos.

## Uso y política

Proyecto independiente para uso personal; no está patrocinado ni respaldado por Spotify. El nombre actual es heredado: antes de distribuirlo públicamente debe revisarse frente a las restricciones de marca de Spotify, que desaconsejan nombres que comiencen por “Spot”.

No uses contenido de Spotify para entrenar o alimentar modelos de IA. La política restringe usos comerciales y monetización de aplicaciones de streaming; contempla algunos usos comerciales limitados de aplicaciones sin streaming, por lo que no existe una prohibición universal de monetizar toda aplicación. Consulta los términos antes de distribuir o monetizar. [Spotify Developer Policy](https://developer.spotify.com/policy).
