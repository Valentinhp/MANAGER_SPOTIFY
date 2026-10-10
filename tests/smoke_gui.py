"""Prueba local de navegación: ninguna petición real ni modificación remota."""
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock,patch
from src.gui.main_window import build_main_window
from src.gui import main_modern

def main():
    sp=Mock()
    def response(value):
        def call(*args,**kwargs):
            assert threading.current_thread() is not threading.main_thread(), 'Red en el hilo de Tk'
            return value
        return call
    sp.current_user.side_effect=response({'id':'local'})
    sp.current_user_playlists.side_effect=response({'items':[],'next':None})
    sp._get.side_effect=response({'items':[],'next':None})
    failures=[]
    with tempfile.TemporaryDirectory() as directory, patch('src.utils.assignments.DATA_DIR',Path(directory)),patch('src.utils.ai_history.HISTORY_FILE',Path(directory)/'ai_history.json'),patch('tkinter.messagebox.showerror',side_effect=lambda *args,**kwargs:failures.append(args)):
        root=build_main_window(sp,smoke=True)
        root.report_callback_exception=lambda *args:failures.append(args)
        pages=[main_modern.ventana_ai_mood,main_modern.ventana_ai_chat,main_modern.ventana_ver_playlists,main_modern.ventana_crear_playlist,
            main_modern.ventana_vaciar_playlists,main_modern.ventana_limpiar_playlists,main_modern.ventana_eliminar_playlists,
            main_modern.ventana_busqueda_avanzada,main_modern.ventana_top_tracks,main_modern.VentanaGestorAutomatico,
            main_modern.ventana_asignar_artista_playlist,main_modern.VentanaGestionarAsignaciones,main_modern.VentanaSincronizarAsignaciones,
            main_modern.ventana_sincronizar_podcasts_data,main_modern.VentanaAdminPodcasts,main_modern.ventana_artistapy,main_modern.ventana_log_viewer]
        from src.gui.ai_history import ventana_ai_history
        from src.gui.ai_fusion import ventana_ai_fusion
        from src.gui.ai_profile import ventana_ai_profile
        from src.gui.ai_context import ventana_ai_context
        pages += [ventana_ai_history,ventana_ai_fusion,ventana_ai_profile,ventana_ai_context]
        for page in pages:
            root.show_frame(page)
            deadline=time.monotonic()+0.25
            while time.monotonic()<deadline:
                root.update();time.sleep(0.01)
        root.destroy()
    if failures:raise AssertionError(failures)
    print(f'{len(pages)} pantallas abiertas sin red real ni errores de Tk')

if __name__=='__main__':main()
