import customtkinter as ctk
from tkinter import ttk,messagebox,simpledialog
from .async_tasks import run_job
from ..utils.assignments import load_assignments,save_assignments
from ..utils.spotify_utils import (search,obtener_playlists_usuario,crear_playlist,obtener_canciones_artista,
    agregar_canciones_a_playlist,get_podcast_episodes,get_playlist_items,playlist_add_items,obtener_artistas_seguidos,obtener_podcasts_guardados)

def assignments_view(parent,sp,kind='artist',sync_only=False):
    frame=ctk.CTkFrame(parent)
    is_artist=kind=='artist'
    ctk.CTkLabel(frame,text='Asignaciones de artistas' if is_artist else 'Asignaciones de podcasts',font=('Segoe UI',24,'bold')).pack(pady=12)
    state={'rows':[],'sources':{},'playlists':{}}
    controls=[]
    if not sync_only:
        query=ctk.CTkEntry(frame,placeholder_text='Buscar artista' if is_artist else 'Buscar podcast')
        query.pack(fill='x',padx=15,pady=5)
        search_bar=ctk.CTkFrame(frame);search_bar.pack(fill='x',padx=15,pady=5)
        sources=ctk.CTkOptionMenu(frame,values=['Selecciona un resultado'],width=600)
        sources.pack(fill='x',padx=15,pady=5)
        destinations=ctk.CTkOptionMenu(frame,values=['Cargando playlists…'],width=600)
        destinations.pack(fill='x',padx=15,pady=5)
        def found(rows):
            state['sources']={f'{name} ({sid[:8]})':(sid,name) for sid,name,*_ in rows}
            values=list(state['sources']) or ['Sin resultados']
            sources.configure(values=values);sources.set(values[0])
        def find():
            text=query.get().strip()
            if not text:return
            def work():
                key='artists' if is_artist else 'shows'
                response=search(sp,text,'artist' if is_artist else 'show',20)
                return [(row['id'],row['name']) for row in response[key]['items'] if row]
            run_job(frame,work,found,controls=controls)
        def saved():
            run_job(frame,lambda:obtener_artistas_seguidos(sp) if is_artist else obtener_podcasts_guardados(sp),found,controls=controls)
        for label,action in [('Buscar',find),('Artistas seguidos' if is_artist else 'Podcasts guardados',saved)]:
            button=ctk.CTkButton(search_bar,text=label,command=action)
            button.pack(side='left',padx=5,pady=5);controls.append(button)
        def playlists_loaded(rows):
            state['playlists']={f'{name} ({pid[:8]})':(pid,name) for pid,name,_ in rows}
            values=list(state['playlists']) or ['Sin playlists']
            destinations.configure(values=values);destinations.set(values[0])
        def refresh_playlists():run_job(frame,lambda:obtener_playlists_usuario(sp),playlists_loaded)
        def new_playlist():
            title=simpledialog.askstring('Playlist','Nombre de la nueva playlist:',parent=frame)
            if title:run_job(frame,lambda:crear_playlist(sp,title),lambda _:refresh_playlists(),controls=controls)
        create_button=ctk.CTkButton(search_bar,text='Nueva playlist',command=new_playlist)
        create_button.pack(side='left',padx=5);controls.append(create_button)
        def assign():
            source=state['sources'].get(sources.get());destination=state['playlists'].get(destinations.get())
            if not source or not destination:return
            if is_artist:
                row={'artista_id':source[0],'artista_nombre':source[1],'playlist_id':destination[0],'playlist_nombre':destination[1]}
            else:row={'podcast':source[0],'podcast_nombre':source[1],'playlist':destination[0],'playlist_nombre':destination[1]}
            skey,pkey=('artista_id','playlist_id') if is_artist else ('podcast','playlist')
            if any(r[skey]==row[skey] and r[pkey]==row[pkey] for r in state['rows']):return
            state['rows'].append(row);save_assignments(state['rows'],kind);render()
        assign_button=ctk.CTkButton(frame,text='Asignar a playlist',command=assign)
        assign_button.pack(pady=5);controls.append(assign_button)
        refresh_playlists()
    tree=ttk.Treeview(frame,columns=('source','playlist'),show='headings',selectmode='extended')
    tree.heading('source',text='Artista' if is_artist else 'Podcast');tree.heading('playlist',text='Playlist')
    tree.pack(fill='both',expand=True,padx=15,pady=10)
    status=ctk.CTkLabel(frame,text='Listo');status.pack(pady=5)
    def render():
        tree.delete(*tree.get_children())
        for i,row in enumerate(state['rows']):
            source=row.get('artista_nombre',row.get('podcast_nombre',row.get('podcast','')))
            dest=row.get('playlist_nombre',row.get('playlist_id',row.get('playlist','')))
            tree.insert('','end',iid=str(i),values=(source,dest))
    def loaded(rows):state['rows']=rows;render()
    def delete():
        selected={int(i) for i in tree.selection()}
        if selected:
            rows=[r for i,r in enumerate(state['rows']) if i not in selected]
            save_assignments(rows,kind);state['rows']=rows;render()
    def synchronize(all_rows=False):
        selected={int(i) for i in tree.selection()}
        rows=[dict(r) for i,r in enumerate(state['rows']) if all_rows or i in selected]
        if not rows:return messagebox.showinfo('Selección','Selecciona asignaciones para sincronizar.',parent=frame)
        status.configure(text='Sincronizando…')
        def work():
            reports=[]
            for row in rows:
                try:
                    if is_artist:
                        count=agregar_canciones_a_playlist(sp,row['playlist_id'],obtener_canciones_artista(sp,row['artista_id']))
                        reports.append(f'{row.get("artista_nombre",row["artista_id"])}: {count} canciones nuevas')
                    else:
                        existing=set(get_playlist_items(sp,row['playlist']))
                        pending=[uri for uri in get_podcast_episodes(sp,row['podcast']) if uri not in existing]
                        if pending:playlist_add_items(sp,row['playlist'],pending)
                        reports.append(f'{row.get("podcast_nombre",row["podcast"])}: {len(pending)} episodios nuevos')
                except Exception as error:reports.append(f'Error: {error}')
            return reports
        def done(reports):
            status.configure(text='Sincronización finalizada')
            messagebox.showinfo('Resultado','\n'.join(reports),parent=frame)
        run_job(frame,work,done,controls=controls)
    bar=ctk.CTkFrame(frame);bar.pack(padx=15,pady=10,fill='x')
    for label,action in [('Eliminar asignación',delete),('Sincronizar seleccionadas',lambda:synchronize()),('Sincronizar todas',lambda:synchronize(True))]:
        button=ctk.CTkButton(bar,text=label,command=action)
        button.pack(side='left',padx=5,pady=5);controls.append(button)
    run_job(frame,lambda:load_assignments(kind),loaded,controls=controls)
    return frame
