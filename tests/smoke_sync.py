"""Ejercita sincronización de podcasts y artistas sin peticiones reales."""
import threading
import time
from unittest.mock import Mock,patch
import customtkinter as ctk
from tkinter import ttk
from src.gui.modern_assignments import assignments_view
from src.utils.progress import report_progress,report_added
from src.utils.spotify_rate_limit import SpotifyRateLimitError


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def pump(root,condition):
    deadline=time.monotonic()+5
    while not condition() and time.monotonic()<deadline:
        root.update();time.sleep(.01)
    assert condition(),'La sincronización no terminó'


def main():
    main_thread=threading.get_ident()
    root=ctk.CTk()
    root.withdraw()
    for kind,limited in (('podcast',False),('artist',False),('podcast',True),('artist',True)):
        errors=[];events=[];reports=[];completed=[]
        root.report_callback_exception=lambda *args:errors.append(args)
        root.job_started=lambda:None
        root.job_finished=lambda:completed.append(True)
        def progress(*args):
            assert threading.get_ident()==main_thread
            events.append(args)
        root.job_progress=progress
        sp=Mock()
        sp.show.return_value={'name':'Mi podcast'}
        rows=[{'podcast':'show1','playlist':'p1'},{'podcast':'show2','playlist':'p2'}] if kind=='podcast' else [
            {'artista_id':'a1','artista_nombre':'Artista uno','playlist_id':'p1'},
            {'artista_id':'a2','artista_nombre':'Artista dos','playlist_id':'p2'}]
        if limited:
            rows.append({'podcast':'show3','playlist':'p3'} if kind=='podcast' else {'artista_id':'a3','artista_nombre':'Artista tres','playlist_id':'p3'})
        calls=[]
        def episodes(*args):
            assert threading.get_ident()!=main_thread
            calls.append(args)
            if limited and len(calls)==2:
                raise SpotifyRateLimitError(79325)
            report_progress(1,2,'Leyendo episodios')
            time.sleep(.12)
            return ['spotify:episode:e1','spotify:episode:e2']
        def add(*args):
            assert threading.get_ident()!=main_thread
            report_progress(1,2,'Agregando elementos')
            time.sleep(.12)
            report_progress(2,2,'Elementos agregados')
            report_added(2)
            return 2
        with patch('src.gui.modern_assignments.load_assignments',return_value=rows), \
             patch('src.gui.modern_assignments.save_assignments'), \
             patch('src.gui.modern_assignments.obtener_playlists_usuario',return_value=[('p1','Música para trabajar',0),('p2','Charlas favoritas',0),('p3','Pendiente',0)]), \
             patch('src.gui.modern_assignments.get_playlist_items',return_value=[]), \
             patch('src.gui.modern_assignments.get_podcast_episodes',side_effect=episodes), \
             patch('src.gui.modern_assignments.playlist_add_items',side_effect=add), \
             patch('src.gui.modern_assignments.obtener_canciones_artista',side_effect=episodes), \
             patch('src.gui.modern_assignments.agregar_canciones_a_playlist',side_effect=add), \
             patch('tkinter.messagebox.showinfo',side_effect=lambda title,text,**kwargs:reports.append(text)):
            frame=assignments_view(root,sp,kind,sync_only=True)
            frame.pack(fill='both',expand=True)
            pump(root,lambda:len(completed)==1)
            tree=next(widget for widget in descendants(frame) if isinstance(widget,ttk.Treeview))
            assert [tree.item(item,'values')[1] for item in tree.get_children()]==['Música para trabajar','Charlas favoritas']+(['Pendiente'] if limited else [])
            button=next(widget for widget in descendants(frame) if isinstance(widget,ctk.CTkButton) and widget.cget('text')=='Sincronizar todas')
            button.invoke()
            pump(root,lambda:len(completed)==2)
            assert not errors,errors
            assert any('Música para trabajar' in message for _,_,message in events)
            assert any(0<done<total for done,total,_ in events if total)
            if not limited:assert events[-1][0]==events[-1][1]==2
            assert reports and 'Música para trabajar' in reports[-1] and 'Charlas favoritas' in reports[-1]
            assert f'Total: {2 if limited else 4}' in reports[-1]
            if limited:
                assert '2 asignaciones pendientes' in reports[-1]
                assert len(calls)==2
                assert '22 h' in reports[-1]
                labels=[widget.cget('text') for widget in descendants(frame) if isinstance(widget,ctk.CTkLabel)]
                assert any('Sincronización detenida' in text for text in labels)
                assert any('1/3 asignaciones procesadas' in text for text in labels)
            assert button.cget('state')=='normal'
        frame.destroy()
    root.destroy()
    print('Sincronizaciones verificadas: progreso, nombres, conteo y detención por 429 sin perder lo añadido')


if __name__=='__main__':main()
