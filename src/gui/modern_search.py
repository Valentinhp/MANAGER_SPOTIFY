import customtkinter as ctk
from tkinter import ttk,messagebox
from .async_tasks import run_job
from ..utils.spotify_utils import search,user_playlist_create,playlist_add_items,obtener_canciones_artista,obtener_playlists_usuario,agregar_canciones_a_playlist,artists
from ..utils.ai_recommender import recomendar_canciones
from ..utils.ai_playlist_builder import resolve_suggestions

def search_view(parent,sp,artist_mode=False,top=False):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Discografía del artista' if artist_mode else 'Búsqueda avanzada',font=('Segoe UI',24,'bold')).pack(pady=12)
    query=ctk.CTkEntry(frame,placeholder_text='Nombre del artista' if artist_mode else 'Frase o tema / emoción')
    query.pack(fill='x',padx=15,pady=5)
    opts=ctk.CTkFrame(frame)
    opts.pack(fill='x',padx=15,pady=5)
    mode=ctk.CTkOptionMenu(opts,values=['Frase','Tema / emoción (IA)'])
    if not artist_mode:mode.pack(side='left',padx=5,pady=5)
    count=ctk.CTkEntry(opts,width=70);count.insert(0,'10' if top else '50');count.pack(side='left',padx=5,pady=5)
    ctk.CTkLabel(opts,text='Máximo (1–1000)').pack(side='left',padx=5)
    order=ctk.CTkOptionMenu(opts,values=['Nombre','Fecha','Duración'])
    order.pack(side='left',padx=5)
    collab=ctk.CTkOptionMenu(opts,values=['Todas','Solo artista','Solo colaboraciones'])
    if artist_mode:collab.pack(side='left',padx=5)
    genre=ctk.CTkEntry(frame,placeholder_text='Géneros opcionales, separados por coma')
    genre.pack(fill='x',padx=15,pady=5)
    artist_tree=ttk.Treeview(frame,columns=('artist',),show='headings',height=3)
    artist_tree.heading('artist',text='Artistas encontrados: doble clic para cargar discografía')
    if artist_mode:artist_tree.pack(fill='x',padx=15,pady=5)
    tree=ttk.Treeview(frame,columns=('title','artist','date'),show='headings',selectmode='extended')
    for key,title in [('title','Título'),('artist','Artista'),('date','Fecha')]:tree.heading(key,text=title)
    tree.pack(fill='both',expand=True,padx=15,pady=5)
    bar=ctk.CTkFrame(frame);bar.pack(fill='x',padx=15,pady=5)
    title=ctk.CTkEntry(bar,placeholder_text='Nombre de nueva playlist');title.insert(0,'Mi playlist');title.pack(side='left',padx=5,pady=5)
    existing=ctk.CTkOptionMenu(bar,values=['Cargando playlists…'],width=240)
    existing.pack(side='left',padx=5)
    status=ctk.CTkLabel(frame,text='Selecciona canciones; si no seleccionas ninguna se usan todos los resultados.')
    status.pack(pady=5)
    state={'tracks':[],'playlists':{}}
    controls=[]
    def parameters():
        try:n=max(1,min(1000,int(count.get())))
        except ValueError:raise ValueError('La cantidad debe ser un número entre 1 y 1000.')
        return n,order.get(),collab.get(),[g.strip().lower() for g in genre.get().split(',') if g.strip()]
    def filter_tracks(tracks,params,artist_id=None):
        n,sort,coll,genres=params
        values=[t for t in tracks if t and t.get('id') and t.get('uri')]
        if artist_id:values=[t for t in values if any(a.get('id')==artist_id for a in t.get('artists',[]))]
        if coll=='Solo artista':values=[t for t in values if len(t.get('artists',[]))==1]
        if coll=='Solo colaboraciones':values=[t for t in values if len(t.get('artists',[]))>1]
        if genres:
            ids=list({a['id'] for t in values for a in t.get('artists',[]) if a.get('id')})
            details=artists(sp,ids)['artists']
            genre_map={a['id']:a.get('genres',[]) for a in details if a}
            values=[t for t in values if any(any(g in ag.lower() for ag in genre_map.get(a.get('id'),[])) for a in t.get('artists',[]) for g in genres)]
        unique={t['id']:t for t in values}
        key={'Nombre':lambda t:t.get('name','').casefold(),'Fecha':lambda t:t.get('album',{}).get('release_date',''),'Duración':lambda t:t.get('duration_ms',0)}[sort]
        return sorted(unique.values(),key=key,reverse=sort=='Fecha')[:n]
    def display(tracks):
        state['tracks']=tracks
        tree.delete(*tree.get_children())
        for t in tracks:tree.insert('','end',iid=t['id'],values=(t.get('name',''),', '.join(a.get('name','') for a in t.get('artists',[])),t.get('album',{}).get('release_date','')))
        status.configure(text=f'{len(tracks)} resultados. Spotify proporciona los títulos y artistas.')
    def search_now():
        text=query.get().strip()
        if not text:return
        try:params=parameters()
        except ValueError as error:return messagebox.showerror('Cantidad',str(error),parent=frame)
        topic=mode.get()!='Frase'
        genres=list(params[3])
        status.configure(text='Buscando…')
        if artist_mode:
            def done(response):
                artist_tree.delete(*artist_tree.get_children())
                for a in response['artists']['items']:
                    if a:artist_tree.insert('','end',iid=a['id'],values=(a['name'],))
                status.configure(text='Selecciona un artista con doble clic.')
            run_job(frame,lambda:search(sp,text,'artist',10),done,controls=controls)
        else:
            def work():
                if topic:
                    suggestions=recomendar_canciones(text+' Géneros: '+', '.join(genres),min(params[0],50))
                    tracks=[r['track'] for r in resolve_suggestions(sp,suggestions) if r['selected']]
                else:tracks=search(sp,text,'track',params[0])['tracks']['items']
                return filter_tracks(tracks,params)
            run_job(frame,work,display,controls=controls)
    def choose_artist(_):
        if not artist_tree.selection():return
        artist_id=artist_tree.selection()[0]
        try:params=parameters()
        except ValueError as error:return messagebox.showerror('Cantidad',str(error),parent=frame)
        status.configure(text='Obteniendo discografía…')
        run_job(frame,lambda:filter_tracks(obtener_canciones_artista(sp,artist_id),params,artist_id),display,controls=controls)
    def chosen():
        ids=set(tree.selection())
        return [t for t in state['tracks'] if not ids or t['id'] in ids]
    def create():
        tracks=chosen();name=title.get().strip() or 'Mi playlist'
        if not tracks:return
        def work():
            playlist=user_playlist_create(sp,'',name,False,'')
            try:playlist_add_items(sp,playlist['id'],[t['uri'] for t in tracks])
            except Exception as error:raise RuntimeError(f'Playlist «{name}» ({playlist["id"]}) creada, pero la carga falló. Revísala antes de reintentar.') from error
            return playlist['id']
        run_job(frame,work,lambda pid:messagebox.showinfo('Creada',f'Playlist creada: {name}',parent=frame),controls=controls)
    def append():
        pid=state['playlists'].get(existing.get());tracks=chosen()
        if not pid or not tracks:return
        run_job(frame,lambda:agregar_canciones_a_playlist(sp,pid,tracks),lambda n:messagebox.showinfo('Actualizada',f'{n} canciones agregadas.',parent=frame),controls=controls)
    for label,action in [('Buscar',search_now),('Crear playlist',create),('Agregar a existente',append)]:
        button=ctk.CTkButton(frame,text=label,command=action)
        button.pack(pady=3);controls.append(button)
    def playlists_loaded(rows):
        state['playlists']={f'{name} ({pid[:8]})':pid for pid,name,_ in rows}
        values=list(state['playlists']) or ['Sin playlists']
        existing.configure(values=values);existing.set(values[0])
    run_job(frame,lambda:obtener_playlists_usuario(sp),playlists_loaded)
    artist_tree.bind('<Double-1>',choose_artist)
    query.bind('<Return>',lambda _:search_now())
    return frame

def ventana_busqueda_avanzada(parent,sp):return search_view(parent,sp)
def ventana_artistas(parent,sp,top=False):return search_view(parent,sp,True,top)
