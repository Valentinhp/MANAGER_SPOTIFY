import json
import webbrowser
from datetime import datetime
from tkinter import ttk, messagebox
import customtkinter as ctk
from .async_tasks import run_job
from ..utils.ai_recommender import recomendar_canciones, sugerir_nombre_playlist
from ..utils.ai_playlist_builder import resolve_suggestions, build_playlist
from ..utils.ai_history import save_generation, attach_playlist
from ..utils.covers import load_cover

def ventana_ai_mood(parent, sp, chat=False, initial_prompt=''):
    frame = ctk.CTkFrame(parent, fg_color='#121212')
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(5, weight=1)
    ctk.CTkLabel(frame, text='Chat musical' if chat else '✨ Radio de Ánimo (IA)', font=('Segoe UI', 24, 'bold')).grid(row=0, column=0, padx=20, pady=12, sticky='w')
    prompt = ctk.CTkEntry(frame, placeholder_text='Una noche tranquila, indie mexicano, sin reggaetón…')
    prompt.grid(row=1, column=0, padx=20, pady=5, sticky='ew')
    if initial_prompt:
        prompt.insert(0,initial_prompt)
    options = ctk.CTkFrame(frame)
    options.grid(row=2, column=0, padx=20, pady=5, sticky='ew')
    arc = ctk.BooleanVar(value=False)
    hour = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(options, text='Arco de energía', variable=arc).pack(side='left', padx=10, pady=8)
    ctk.CTkCheckBox(options, text='Usar hora local', variable=hour).pack(side='left', padx=10)
    transcript = ctk.CTkTextbox(frame, height=90)
    if chat:
        transcript.grid(row=3, column=0, padx=20, pady=5, sticky='ew')
        transcript.configure(state='disabled')
    tools = ctk.CTkFrame(frame)
    tools.grid(row=4, column=0, padx=20, pady=5, sticky='ew')
    preview = ctk.CTkFrame(frame)
    preview.grid(row=5, column=0, padx=20, pady=5, sticky='nsew')
    preview.grid_columnconfigure(0, weight=1)
    preview.grid_rowconfigure(0, weight=1)
    tree = ttk.Treeview(preview, columns=('use', 'title', 'artist', 'status'), show='headings', selectmode='browse')
    for key, label, width in [('use','✓',45),('title','Título',240),('artist','Artista',180),('status','Spotify',110)]:
        tree.heading(key, text=label)
        tree.column(key, width=width, stretch=key in ('title','artist'))
    tree.grid(row=0, column=0, sticky='nsew')
    scroll = ttk.Scrollbar(preview, command=tree.yview)
    scroll.grid(row=0,column=1,sticky='ns')
    tree.configure(yscrollcommand=scroll.set)
    cover = ctk.CTkLabel(preview, text='Portada')
    cover.grid(row=0,column=2,padx=10)
    details = ctk.CTkFrame(frame)
    details.grid(row=6,column=0,padx=20,pady=5,sticky='ew')
    name = ctk.CTkEntry(details, placeholder_text='Nombre de playlist', width=250)
    name.insert(0,'Radio de Ánimo')
    name.pack(side='left',padx=5,pady=8)
    description = ctk.CTkEntry(details, placeholder_text='Descripción')
    description.pack(side='left',fill='x',expand=True,padx=5)
    public = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(details,text='Pública',variable=public,width=90).pack(side='left',padx=5)
    status = ctk.CTkLabel(frame,text='Selecciona canciones con doble clic. Spotify proporciona los resultados y portadas.')
    status.grid(row=8,column=0,padx=20,pady=8,sticky='w')
    state = {'rows': [], 'suggested': [], 'history': [], 'generation': None, 'playlist': None, 'cover_token': 0}
    controls = []

    def display(rows):
        tree.delete(*tree.get_children())
        for i,row in enumerate(rows):
            song=row['suggestion']
            tree.insert('', 'end', iid=str(i), values=('☑' if row['selected'] else '☐',song['title'],song['artist'],row['status']))
        status.configure(text=f'{sum(r["selected"] for r in rows)} canciones seleccionadas · doble clic para cambiar')

    def toggle(event):
        item=tree.identify_row(event.y)
        if not item:
            return
        row=state['rows'][int(item)]
        if row['track'] and row['status'] != 'Duplicada':
            row['selected']=not row['selected']
            display(state['rows'])

    def show_cover(_event):
        selection=tree.selection()
        if not selection:
            return
        track=state['rows'][int(selection[0])]['track']
        images=(track or {}).get('album',{}).get('images',[])
        state['cover_token']+=1
        token=state['cover_token']
        cover.configure(image=None,text='Sin portada')
        if not images:
            return
        def show(image):
            if token == state['cover_token'] and image:
                cover.image=ctk.CTkImage(image,image,size=(130,130))
                cover.configure(image=cover.image,text='')
        run_job(frame,lambda:load_cover(images[0]['url']),show,on_error=lambda e:cover.configure(text='Portada no disponible'))

    def generate(more=False):
        text=prompt.get().strip()
        if not text:
            return messagebox.showinfo('Ánimo','Describe qué quieres escuchar.',parent=frame)
        request=text+(f' Hora local: {datetime.now().strftime("%H:%M")}' if hour.get() else '')
        order='arco' if arc.get() else 'normal'
        exclusions=list(state['suggested']) if more else []
        history=list(state['history'][-20:]) if chat else None
        status.configure(text='Generando y buscando canciones…')
        def work():
            songs=recomendar_canciones(request,excluir=exclusions,orden=order,historial=history)
            rows=resolve_suggestions(sp,songs)
            entry=save_generation(request,songs)
            return songs,rows,entry
        def done(value):
            songs,rows,entry=value
            state['rows']=rows
            state['suggested'].extend(s for s in songs if s not in state['suggested'])
            state['generation']=entry
            state['playlist']=None
            state['history'].extend([{'role':'user','content':request},{'role':'assistant','content':json.dumps({'songs':songs},ensure_ascii=False)}])
            if chat:
                transcript.configure(state='normal')
                transcript.insert('end',f'Tú: {text}\nIA: {len(songs)} sugerencias nuevas\n')
                transcript.see('end')
                transcript.configure(state='disabled')
            display(rows)
        run_job(frame,work,done,controls=controls)

    def suggest_name():
        text=prompt.get().strip()
        songs=[r['suggestion'] for r in state['rows'] if r['selected']]
        def done(value):
            name.delete(0,'end'); name.insert(0,value[0])
            description.delete(0,'end'); description.insert(0,value[1])
        run_job(frame,lambda:sugerir_nombre_playlist(text,songs),done,controls=controls)

    def create():
        if state['playlist']:
            return messagebox.showinfo('Ya creada',f'Esta generación ya creó la playlist {state["playlist"]}.',parent=frame)
        rows=[dict(r) for r in state['rows']]
        title,desc,is_public=name.get(),description.get(),public.get()
        generation=state['generation']
        def work():
            playlist=build_playlist(sp,title,desc,rows,is_public)
            # Return the successful remote result even if local history cannot be updated.
            warning=None
            try:
                attach_playlist(generation,playlist['id'])
            except Exception as error:
                warning=str(error)
            return playlist,warning
        def done(value):
            playlist,warning=value
            state['playlist']=playlist['id']
            status.configure(text=f'Playlist creada: {playlist["id"]}')
            messagebox.showinfo('Playlist creada',title+(f'\nHistorial: {warning}' if warning else ''),parent=frame)
        run_job(frame,work,done,controls=controls)

    def open_selected():
        selection=tree.selection()
        if selection:
            track=state['rows'][int(selection[0])]['track']
            if track:
                webbrowser.open(track.get('external_urls',{}).get('spotify',f'https://open.spotify.com/track/{track["id"]}'))

    for label,action in [('Refinar' if chat else 'Generar 15',lambda:generate()),('🔄 Dame otras 15',lambda:generate(True)),('🎲 Sugerir nombre',suggest_name),('Abrir en Spotify',open_selected),('Crear playlist',create)]:
        button=ctk.CTkButton(tools,text=label,command=action,width=135)
        button.pack(side='left',padx=4,pady=8)
        controls.append(button)
    tree.bind('<Double-1>',toggle)
    tree.bind('<<TreeviewSelect>>',show_cover)
    return frame
