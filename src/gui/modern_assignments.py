import customtkinter as ctk
from tkinter import ttk,messagebox,simpledialog
from .async_tasks import run_job
from .job_progress import JobProgress
from ..utils.progress import report_progress,progress_range
from ..utils.playlist_names import resolve_playlist_names,playlist_label
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
    tree=ttk.Treeview(frame,columns=('source','playlist'),show='headings',selectmode='extended')
    tree.heading('source',text='Artista' if is_artist else 'Podcast');tree.heading('playlist',text='Playlist')
    tree.pack(fill='both',expand=True,padx=15,pady=10)
    status=ctk.CTkLabel(frame,text='Listo');status.pack(pady=5)
    progress=JobProgress(frame);progress.pack(fill='x',padx=15,pady=5)
    def render():
        tree.delete(*tree.get_children())
        for i,row in enumerate(state['rows']):
            source=row.get('artista_nombre',row.get('podcast_nombre',row.get('podcast','')))
            dest=playlist_label(row.get('playlist_id',row.get('playlist','')),saved=row.get('playlist_nombre'))
            tree.insert('','end',iid=str(i),values=(source,dest))
    def load_view():
        rows=[dict(row) for row in load_assignments(kind)]
        try:catalog=obtener_playlists_usuario(sp)
        except Exception:catalog=[]
        names=resolve_playlist_names(sp,[row.get('playlist_id',row.get('playlist')) for row in rows],
            known={pid:name for pid,name,_ in catalog})
        for row in rows:
            pid=row.get('playlist_id',row.get('playlist'))
            if pid in names:row['playlist_nombre']=names[pid]
            if not is_artist and not row.get('podcast_nombre'):
                try:
                    value=sp.show(row['podcast']).get('name')
                    if isinstance(value,str) and value.strip():row['podcast_nombre']=value
                except Exception:pass
        save_assignments(rows,kind)
        return rows,catalog
    def loaded(value):
        rows,catalog=value
        state['rows']=rows;render()
        if not sync_only:playlists_loaded(catalog)
        progress.finish(f'{len(rows)} asignaciones cargadas')
    def delete():
        selected={int(i) for i in tree.selection()}
        if selected:
            rows=[r for i,r in enumerate(state['rows']) if i not in selected]
            save_assignments(rows,kind);state['rows']=rows;render()
    def synchronize(all_rows=False):
        selected={int(i) for i in tree.selection()}
        rows=[dict(r) for i,r in enumerate(state['rows']) if all_rows or i in selected]
        if not rows:return messagebox.showinfo('Selección','Selecciona asignaciones para sincronizar.',parent=frame)
        counter={'added':0}
        unit='canciones' if is_artist else 'episodios'
        status.configure(text=f'Sincronizando · 0 {unit} nuevos agregados')
        def added(count):
            counter['added']+=count
            status.configure(text=f'Sincronizando · {counter["added"]} {unit} nuevos agregados')
        def work():
            reports=[]
            for index,row in enumerate(rows):
                source=row.get('artista_nombre') or row.get('podcast_nombre') or row.get('artista_id',row.get('podcast',''))
                destination=playlist_label(row.get('playlist_id',row.get('playlist')),saved=row.get('playlist_nombre'))
                label=f'{source} → {destination}'
                report_progress(index,len(rows),f'Asignación {index+1}/{len(rows)}: {label}')
                try:
                    if is_artist:
                        with progress_range(index,index+.75,len(rows),label):
                            tracks=obtener_canciones_artista(sp,row['artista_id'])
                        with progress_range(index+.75,index+1,len(rows),label):
                            count=agregar_canciones_a_playlist(sp,row['playlist_id'],tracks)
                        reports.append(f'{label}: {count} canciones nuevas')
                    else:
                        with progress_range(index,index+.2,len(rows),label):
                            existing=set(get_playlist_items(sp,row['playlist']))
                        with progress_range(index+.2,index+.7,len(rows),label):
                            pending=list(dict.fromkeys(uri for uri in get_podcast_episodes(sp,row['podcast']) if uri not in existing))
                        with progress_range(index+.7,index+1,len(rows),label):
                            if pending:playlist_add_items(sp,row['playlist'],pending)
                        reports.append(f'{label}: {len(pending)} episodios nuevos')
                except Exception as error:reports.append(f'{label} · Error: {error}')
                report_progress(index+1,len(rows),f'{index+1}/{len(rows)} asignaciones procesadas · {label}')
            return reports
        def done(reports):
            summary=f'Total: {counter["added"]} {unit} nuevos agregados'
            status.configure(text=f'Sincronización finalizada · {summary}')
            progress.finish(f'{len(rows)}/{len(rows)} asignaciones procesadas; revisa el resultado de cada una')
            messagebox.showinfo('Resultado',summary+'\n\n'+'\n'.join(reports),parent=frame)
        run_job(frame,work,done,controls=controls,on_progress=progress.update_progress,on_added=added)
    bar=ctk.CTkFrame(frame);bar.pack(padx=15,pady=10,fill='x')
    for label,action in [('Eliminar asignación',delete),('Sincronizar seleccionadas',lambda:synchronize()),('Sincronizar todas',lambda:synchronize(True))]:
        button=ctk.CTkButton(bar,text=label,command=action)
        button.pack(side='left',padx=5,pady=5);controls.append(button)
    run_job(frame,load_view,loaded,controls=controls,on_progress=progress.update_progress)
    return frame
