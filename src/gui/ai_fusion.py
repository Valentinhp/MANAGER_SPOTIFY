import customtkinter as ctk
from tkinter import ttk,messagebox
from .async_tasks import run_job
from ..utils.spotify_utils import get_current_user, current_user_playlists, playlist_items, user_playlist_create, playlist_add_items

def balanced_merge(first,second):
    result,seen=[],set()
    for i in range(max(len(first),len(second))):
        for source in (first,second):
            if i<len(source):
                track=source[i]
                if track and track.get('uri') and track['uri'] not in seen:
                    result.append(track);seen.add(track['uri'])
    return result

def ventana_ai_fusion(parent, sp):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Fusión balanceada de playlists',font=('Segoe UI',24,'bold')).pack(pady=15)
    ctk.CTkLabel(frame,text='Intercala ambas listas localmente, sin enviar su contenido a la IA.').pack(pady=5)
    selectors=ctk.CTkFrame(frame)
    selectors.pack(fill='x',padx=15,pady=10)
    first=ctk.CTkOptionMenu(selectors,values=['Cargando…'],width=300)
    second=ctk.CTkOptionMenu(selectors,values=['Cargando…'],width=300)
    first.pack(side='left',padx=10);second.pack(side='left',padx=10)
    tree=ttk.Treeview(frame,columns=('title','artist'),show='headings')
    tree.heading('title',text='Título');tree.heading('artist',text='Artista')
    tree.pack(fill='both',expand=True,padx=15,pady=10)
    name=ctk.CTkEntry(frame,placeholder_text='Nombre de la tercera playlist')
    name.insert(0,'Fusión balanceada');name.pack(fill='x',padx=15,pady=10)
    state={'playlists':{},'tracks':[],'created':False}
    def load():
        user=get_current_user(sp)['id'];rows=[];offset=0
        while True:
            response=current_user_playlists(sp,offset=offset)
            rows.extend(p for p in response.get('items',[]) if p and p.get('owner',{}).get('id')==user)
            if not response.get('next'):break
            offset+=len(response['items'])
        return rows
    def loaded(rows):
        state['playlists']={f'{p["name"]} ({p["id"][:8]})':p['id'] for p in rows}
        values=list(state['playlists']) or ['Sin playlists propias']
        first.configure(values=values);second.configure(values=values)
        first.set(values[0]);second.set(values[min(1,len(values)-1)])
    def read(pid):
        tracks=[];offset=0
        while True:
            response=playlist_items(sp,pid,offset=offset,limit=50)
            tracks.extend(row.get('item',row.get('track')) for row in response.get('items',[]) if row)
            if not response.get('next'):break
            offset+=len(response['items'])
        return tracks
    def preview():
        a,b=state['playlists'].get(first.get()),state['playlists'].get(second.get())
        if not a or not b or a==b:return messagebox.showinfo('Fusión','Selecciona dos playlists propias distintas.',parent=frame)
        def show(tracks):
            state['tracks']=tracks;state['created']=False
            tree.delete(*tree.get_children())
            for t in tracks:tree.insert('','end',values=(t.get('name',''),', '.join(a.get('name','') for a in t.get('artists',[]))))
        run_job(frame,lambda:balanced_merge(read(a),read(b)),show,controls=(preview_button,create_button))
    def create():
        if not state['tracks'] or state['created']:return
        title=name.get().strip() or 'Fusión balanceada'
        uris=[t['uri'] for t in state['tracks']]
        def work():
            playlist=user_playlist_create(sp,'',title,False,'Fusión local balanceada de dos playlists')
            try:playlist_add_items(sp,playlist['id'],uris)
            except Exception as error:raise RuntimeError(f'Playlist «{title}» ({playlist["id"]}) creada; no se completó la carga. Revísala antes de reintentar.') from error
            return playlist['id']
        def done(pid):
            state['created']=True
            messagebox.showinfo('Creada',f'Playlist creada: {title}',parent=frame)
        run_job(frame,work,done,controls=(preview_button,create_button))
    preview_button=ctk.CTkButton(frame,text='Vista previa de fusión',command=preview)
    preview_button.pack(pady=5)
    create_button=ctk.CTkButton(frame,text='Crear tercera playlist',command=create)
    create_button.pack(pady=5)
    run_job(frame,load,loaded)
    return frame
