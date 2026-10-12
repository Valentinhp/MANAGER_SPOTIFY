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
    scale=root._get_window_scaling()
    width=min(1200,max(760,int(root.winfo_screenwidth()/scale)-40))
    height=min(820,max(480,int(root.winfo_screenheight()/scale)-80))
    root.geometry(f'{width}x{height}')
    root.minsize(min(1000,width),min(640,height))
    root.configure(fg_color='#000000')
    root.grid_rowconfigure(0,weight=1)
    root.grid_columnconfigure(1,weight=1)
    style=ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame',background='#121212')
    style.configure('TLabel',background='#121212',foreground='white')
    style.configure('TButton',background='#1DB954',foreground='white',padding=8)
    style.configure('TEntry',fieldbackground='#252525',foreground='white')
    style.configure('Treeview',background='#121212',fieldbackground='#121212',foreground='white',rowheight=54,borderwidth=0)
    style.configure('Treeview.Heading',background='#121212',foreground='#a7a7a7',padding=8)
    style.map('Treeview',background=[('selected','#168d40')])
    sidebar=ctk.CTkScrollableFrame(root,width=200,fg_color='#000000',corner_radius=0)
    sidebar.grid(row=0,column=0,rowspan=2,sticky='nsew')
    ctk.CTkLabel(sidebar,text='SpotyVManager',font=('Segoe UI',21,'bold'),text_color='#1DB954').pack(padx=12,pady=20)
    content=ctk.CTkFrame(root,fg_color='#121212',corner_radius=0)
    content.grid(row=0,column=1,sticky='nsew',padx=(0,8),pady=8)
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
        cards.pack(fill='x',padx=30,pady=15)
        for column in range(2):cards.grid_columnconfigure(column,weight=1)
        for i,(title,subtitle,factory) in enumerate([
            ('✨ Radio de Ánimo','Describe tu momento y revisa las sugerencias.',ventana_ai_mood),
            ('Canciones parecidas','Indica una canción como referencia en el chat.',ventana_ai_chat),
            ('Buscar artista','Explora su discografía y colaboraciones.',VentanaGestorAutomatico),
            ('Mis playlists','Tus portadas, canciones y colecciones.',lambda p,s:section(p,s,library_pages))]):
            ctk.CTkButton(cards,text=title+'\n\n'+subtitle,height=105,font=('Segoe UI',15,'bold'),fg_color='#202020',hover_color='#303030',
                command=lambda f=factory:show_frame(f)).grid(row=i//2,column=i%2,padx=10,pady=10,sticky='ew')
        ctk.CTkLabel(frame,text='Tu colección',font=('Segoe UI',23,'bold')).pack(anchor='w',padx=40,pady=(18,8))
        shelf=ctk.CTkScrollableFrame(frame,orientation='horizontal',height=190,fg_color='transparent')
        shelf.pack(fill='x',padx=30,pady=5)
        if not smoke:
            from .visual_library import cover_label,image_url
            from ..utils.spotify_utils import current_user_playlists
            def loaded(response):
                playlists=[p for p in response.get('items',[]) if p][:6]
                if not playlists:
                    ctk.CTkLabel(shelf,text='Tus playlists aparecerán aquí.',text_color='#a7a7a7').pack(padx=10,pady=30)
                for item in playlists:
                    card=ctk.CTkFrame(shelf,fg_color='#181818',corner_radius=10)
                    card.pack(side='left',padx=8,pady=5)
                    cover_label(card,image_url(item),110).pack(padx=12,pady=10)
                    ctk.CTkButton(card,text=item.get('name','Playlist'),width=125,fg_color='transparent',hover_color='#282828',command=lambda:navigate(1)).pack(padx=8,pady=(0,8))
            run_job(frame,lambda:current_user_playlists(sp,limit=6),loaded,on_error=lambda _:ctk.CTkLabel(shelf,text='Abre Mis playlists para cargar tu biblioteca.',text_color='#a7a7a7').pack(padx=10,pady=30))
        else:
            ctk.CTkLabel(shelf,text='Tus playlists aparecerán aquí al conectar Spotify.',text_color='#a7a7a7').pack(padx=10,pady=30)
        return frame
    from .ai_history import ventana_ai_history
    from .ai_profile import ventana_ai_profile
    from .ai_fusion import ventana_ai_fusion
    from .ai_context import ventana_ai_context
    from .navigation import section, settings, ventana_biblioteca
    library_pages=[('Biblioteca',ventana_biblioteca),('Crear',ventana_crear_playlist),('Combinar',ventana_ai_fusion),('Duplicados',ventana_limpiar_playlists),('Vaciar',ventana_vaciar_playlists),('Dejar de seguir',ventana_eliminar_playlists)]
    ai_pages=[('Por vibra',ventana_ai_mood),('Chat musical',ventana_ai_chat),('Hora / clima',ventana_ai_context),('Mi gusto',ventana_ai_profile),('Historial',ventana_ai_history)]
    explore_pages=[('Canciones',ventana_busqueda_avanzada),('Artistas',VentanaGestorAutomatico)]
    sync_pages=[('Asignar artista',ventana_asignar_artista_playlist),('Asignaciones',VentanaGestionarAsignaciones),('Sincronizar artistas',VentanaSincronizarAsignaciones),('Podcasts',VentanaAdminPodcasts),('Sincronizar podcasts',ventana_sincronizar_podcasts_data)]
    entries=[('⌂  Inicio',home),('♫  Mis playlists',lambda p,s:section(p,s,library_pages)),('✦  Crear con IA',lambda p,s:section(p,s,ai_pages)),('⌕  Explorar música',lambda p,s:section(p,s,explore_pages)),('↻  Sincronizaciones',lambda p,s:section(p,s,sync_pages)),('⚙  Configuración',settings),('≡  Registro',ventana_log_viewer)]
    nav_buttons=[]
    def navigate(index):
        for i,button in enumerate(nav_buttons):
            button.configure(fg_color='#282828' if i==index else 'transparent',text_color='white' if i==index else '#a7a7a7')
        show_frame(entries[index][1])
    for index,(label,factory) in enumerate(entries):
        if index==5:
            ctk.CTkLabel(sidebar,text='TU APLICACIÓN',text_color='#777777',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=16,pady=(30,8))
        button=ctk.CTkButton(sidebar,text=label,anchor='w',height=44,corner_radius=8,font=('Segoe UI',14,'bold'),fg_color='transparent',hover_color='#202020',command=lambda i=index:navigate(i))
        button.pack(fill='x',padx=8,pady=3)
        nav_buttons.append(button)
    def refresh():
        if not smoke:
            run_job(root,check_spotify_api_status,lambda value:status.configure(text=value[1]),on_error=lambda e:status.configure(text=str(e)))
    ctk.CTkButton(status_bar,text='Actualizar estado',width=140,command=refresh).pack(side='right',padx=5)
    navigate(0)
    refresh()
    return root
