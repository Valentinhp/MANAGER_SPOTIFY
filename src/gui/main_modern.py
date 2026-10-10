import customtkinter as ctk
from tkinter import ttk
from .async_tasks import run_job
from .ai_mood import ventana_ai_mood
from .ai_chat import ventana_ai_chat
from .playlists import ventana_ver_playlists, ventana_crear_playlist, ventana_vaciar_playlists, ventana_limpiar_playlists, ventana_eliminar_playlists
from .search_advanced import ventana_busqueda_avanzada
from .top_tracks import ventana_top_tracks
from .artist_manager import VentanaGestorAutomatico
from .assign_artist import ventana_asignar_artista_playlist
from .manage_assignments import VentanaGestionarAsignaciones
from .sync_assignments import VentanaSincronizarAsignaciones
from .podcasts import ventana_sincronizar_podcasts_data
from .admin_podcasts import VentanaAdminPodcasts
from .artistapy import ventana_artistapy
from .log_viewer import ventana_log_viewer
from ..utils.spotify_utils import check_spotify_api_status

def build_main_window(sp, smoke=False):
    ctk.set_appearance_mode('dark')
    ctk.set_default_color_theme('green')
    root=ctk.CTk()
    root.title('SpotyVManager')
    root.geometry('1200x820')
    root.minsize(1000,700)
    root.configure(fg_color='#121212')
    root.grid_rowconfigure(0,weight=1)
    root.grid_columnconfigure(1,weight=1)
    style=ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame',background='#121212')
    style.configure('TLabel',background='#121212',foreground='white')
    style.configure('TButton',background='#1DB954',foreground='white',padding=8)
    style.configure('TEntry',fieldbackground='#252525',foreground='white')
    style.configure('Treeview',background='#202020',fieldbackground='#202020',foreground='white',rowheight=30)
    style.configure('Treeview.Heading',background='#181818',foreground='white')
    style.map('Treeview',background=[('selected','#168d40')])
    sidebar=ctk.CTkScrollableFrame(root,width=210,fg_color='#181818',corner_radius=0)
    sidebar.grid(row=0,column=0,rowspan=2,sticky='nsew')
    ctk.CTkLabel(sidebar,text='SpotyVManager',font=('Segoe UI',21,'bold'),text_color='#1DB954').pack(padx=12,pady=20)
    content=ctk.CTkFrame(root,fg_color='#121212',corner_radius=0)
    content.grid(row=0,column=1,sticky='nsew')
    state={'frame':None,'jobs':0}
    status_bar=ctk.CTkFrame(root,height=38,corner_radius=0)
    status_bar.grid(row=1,column=1,sticky='ew')
    progress=ctk.CTkProgressBar(status_bar,mode='indeterminate',progress_color='#1DB954',width=180)
    progress.pack(side='right',padx=10,pady=12)
    progress.set(0)
    status=ctk.CTkLabel(status_bar,text='Listo')
    status.pack(side='left',padx=12)
    def started():
        state['jobs']+=1
        progress.configure(mode='indeterminate')
        progress.start()
        status.configure(text=f'{state["jobs"]} tarea(s) en curso…')
    def finished():
        state['jobs']=max(0,state['jobs']-1)
        if state['jobs']==0:
            progress.stop();progress.set(0)
            status.configure(text='Listo')
    def job_progress(done,total,message):
        if total and state['jobs']==1:
            progress.stop()
            progress.configure(mode='determinate')
            progress.set(max(0,min(1,done/total)))
            status.configure(text=f'{done/total:.0%} · {message}')
        else:
            progress.configure(mode='indeterminate')
            progress.start()
            status.configure(text=message)
    root.job_progress=job_progress
    root.job_started=started
    root.job_finished=finished
    def show_frame(factory,*args):
        if state['frame'] and state['frame'].winfo_exists():
            state['frame'].destroy()
        state['frame']=factory(content,sp,*args)
        state['frame'].pack(fill='both',expand=True)
    root.show_frame=show_frame
    def home(parent,sp):
        frame=ctk.CTkFrame(parent,fg_color='#121212')
        ctk.CTkLabel(frame,text='Tu música, a tu manera',font=('Segoe UI',30,'bold')).pack(anchor='w',padx=35,pady=(40,12))
        ctk.CTkLabel(frame,text='Explora, organiza y crea una playlist para cada momento.').pack(anchor='w',padx=35,pady=(0,25))
        cards=ctk.CTkFrame(frame,fg_color='transparent')
        cards.pack(fill='both',expand=True,padx=30,pady=15)
        for column in range(2):cards.grid_columnconfigure(column,weight=1)
        for i,(title,subtitle,factory) in enumerate([
            ('✨ Radio de Ánimo','Describe tu momento y revisa las sugerencias.',ventana_ai_mood),
            ('Canciones parecidas','Indica una canción como referencia en el chat.',ventana_ai_chat),
            ('Buscar artista','Explora su discografía y colaboraciones.',VentanaGestorAutomatico),
            ('Mis playlists','Consulta y organiza tus listas.',ventana_ver_playlists)]):
            ctk.CTkButton(cards,text=title+'\n\n'+subtitle,height=150,font=('Segoe UI',17),fg_color='#202020',hover_color='#174b2b',
                command=lambda f=factory:show_frame(f)).grid(row=i//2,column=i%2,padx=10,pady=10,sticky='ew')
        return frame
    groups=[('Inicio',[('Inicio',home)]),('Playlists',[('Mis playlists',ventana_ver_playlists),('Crear',ventana_crear_playlist),('Vaciar',ventana_vaciar_playlists),('Limpiar duplicados',ventana_limpiar_playlists),('Eliminar',ventana_eliminar_playlists)]),
        ('Podcasts',[('Sincronizar podcasts',ventana_sincronizar_podcasts_data),('Administrar podcasts',VentanaAdminPodcasts)]),
        ('Artistas',[('Buscar artista',VentanaGestorAutomatico),('Asignar a playlist',ventana_asignar_artista_playlist),('Gestionar asignaciones',VentanaGestionarAsignaciones),('Sincronizar artistas',VentanaSincronizarAsignaciones),('Artistapy',ventana_artistapy)]),
        ('Buscar',[('Búsqueda avanzada',ventana_busqueda_avanzada)]),('IA',[('✨ Radio de Ánimo',ventana_ai_mood),('Chat musical',ventana_ai_chat)]),
        ('Top Tracks',[('Top Tracks',ventana_top_tracks)]),('Registro',[('Registro',ventana_log_viewer)])]
    # Additional IA pages are registered when their modules are available.
    from .ai_history import ventana_ai_history
    from .ai_profile import ventana_ai_profile
    from .ai_fusion import ventana_ai_fusion
    from .ai_context import ventana_ai_context
    groups[5][1].extend([('Resumen de gusto',ventana_ai_profile),('Fusionar playlists',ventana_ai_fusion),('Hora / clima',ventana_ai_context),('Historial IA',ventana_ai_history)])
    for section,entries in groups:
        ctk.CTkLabel(sidebar,text=section,text_color='#999999',anchor='w').pack(fill='x',padx=12,pady=(12,2))
        for label,factory in entries:
            ctk.CTkButton(sidebar,text=label,anchor='w',fg_color='transparent',hover_color='#27412e',command=lambda f=factory:show_frame(f)).pack(fill='x',padx=5,pady=2)
    def refresh():
        if not smoke:
            run_job(root,check_spotify_api_status,lambda value:status.configure(text=value[1]),on_error=lambda e:status.configure(text=str(e)))
    ctk.CTkButton(status_bar,text='Actualizar estado',width=140,command=refresh).pack(side='right',padx=5)
    show_frame(home)
    refresh()
    return root
