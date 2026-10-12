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
    with tempfile.TemporaryDirectory() as directory, patch('src.utils.assignments.DATA_DIR',Path(directory)),patch('src.utils.ai_history.HISTORY_FILE',Path(directory)/'ai_history.json'),patch('src.utils.chatgpt_session.SESSION_PATH',Path(directory)/'chatgpt-session.bin'),patch('tkinter.messagebox.showerror',side_effect=lambda *args,**kwargs:failures.append(args)):
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
        from src.gui.navigation import section, settings
        from src.gui.visual_library import ventana_biblioteca
        pages += [ventana_biblioteca,settings,lambda p,s:section(p,s,[('Biblioteca',ventana_biblioteca),('Crear',main_modern.ventana_crear_playlist)])]
        for page in pages:
            root.show_frame(page)
            deadline=time.monotonic()+0.25
            while time.monotonic()<deadline:
                root.update();time.sleep(0.01)
        # Exercise card -> populated detail -> library and stale worker callbacks.
        import customtkinter as ctk
        from PIL import Image
        playlist={'id':'test-list','name':'Biblioteca de prueba','images':[{'url':'mock-cover'}],'owner':{'display_name':'Prueba'}}
        track={'id':'test-track','name':'Canción de prueba','uri':'spotify:track:test-track','artists':[{'name':'Artista de prueba'}],'album':{'images':[{'url':'mock-cover'}]},'duration_ms':183000}
        with patch('src.gui.visual_library.current_user_playlists',side_effect=response({'items':[playlist],'next':None})),patch('src.gui.visual_library.playlist_items',side_effect=response({'items':[{'item':track}],'next':None})),patch('src.gui.visual_library.load_cover',side_effect=response(Image.new('RGB',(160,160),'#1db954'))):
            root.show_frame(ventana_biblioteca)
            def settle():
                deadline=time.monotonic()+0.4
                while time.monotonic()<deadline:
                    root.update();time.sleep(0.01)
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from descendants(child)
            settle()
            card=next(w for w in descendants(root) if isinstance(w,ctk.CTkButton) and w.cget('text')=='Abrir playlist')
            card.invoke();settle()
            assert any(isinstance(w,ctk.CTkLabel) and w.cget('text')==track['name'] for w in descendants(root))
            back=next(w for w in descendants(root) if isinstance(w,ctk.CTkButton) and w.cget('text')=='Biblioteca')
            back.invoke();settle()
            import sys
            if '--snapshot' in sys.argv:
                from PIL import ImageGrab
                root.lift();root.update()
                x,y=root.winfo_rootx(),root.winfo_rooty()
                target=Path('local_backups')/'library-preview.png'
                target.parent.mkdir(exist_ok=True)
                ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height())).save(target)
        root.destroy()
    if failures:raise AssertionError(failures)
    print(f'{len(pages)} pantallas abiertas sin red real ni errores de Tk')

if __name__=='__main__':main()
