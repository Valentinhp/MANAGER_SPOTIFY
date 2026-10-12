"""Visual library; Spotify calls and cover downloads stay in workers."""
import customtkinter as ctk
from .async_tasks import run_job
from .job_progress import JobProgress
from ..utils.covers import load_cover
from ..utils.spotify_utils import current_user_playlists, playlist_items


def cover_label(parent, url, size=160):
    label = ctk.CTkLabel(parent, text='♫', width=size, height=size,
                         fg_color='#282828', corner_radius=8,
                         font=('Segoe UI', 42), text_color='#a7a7a7')
    if url:
        def loaded(value):
            if value:
                label.cover = ctk.CTkImage(value, value, size=(size, size))
                label.configure(image=label.cover, text='')
        run_job(label, lambda: load_cover(url), loaded, on_error=lambda _: None)
    return label


def image_url(item):
    images = item.get('images') or (item.get('album') or {}).get('images') or []
    return images[0].get('url') if images else None


def ventana_biblioteca(parent, sp):
    frame = ctk.CTkFrame(parent, fg_color='#121212', corner_radius=12)
    header = ctk.CTkFrame(frame, fg_color='#183c2b', corner_radius=12)
    header.pack(fill='x', padx=20, pady=(20, 12))
    ctk.CTkLabel(header, text='TU BIBLIOTECA', text_color='#b9d8c6', font=('Segoe UI', 12, 'bold')).pack(anchor='w', padx=24, pady=(18, 0))
    ctk.CTkLabel(header, text='Mis playlists', font=('Segoe UI', 36, 'bold')).pack(anchor='w', padx=24, pady=(0, 18))
    toolbar = ctk.CTkFrame(frame, fg_color='transparent')
    toolbar.pack(fill='x', padx=20, pady=5)
    query = ctk.CTkEntry(toolbar, placeholder_text='Buscar en tu biblioteca', width=260, height=36)
    query.pack(side='left', padx=(0, 10))
    body = ctk.CTkScrollableFrame(frame, fg_color='transparent')
    body.pack(fill='both', expand=True, padx=12, pady=10)
    progress = JobProgress(frame)
    progress.pack(fill='x', padx=20, pady=8)
    state = {'rows': [], 'token': 0}

    def clear():
        for widget in body.winfo_children():
            widget.destroy()

    def detail(item):
        state['token'] += 1
        token = state['token']
        clear()
        top = ctk.CTkFrame(body, fg_color='transparent')
        top.pack(fill='x', pady=12)
        cover_label(top, image_url(item)).pack(side='left', padx=12)
        info = ctk.CTkFrame(top, fg_color='transparent')
        info.pack(side='left', fill='x', expand=True, padx=12)
        ctk.CTkLabel(info, text='PLAYLIST', text_color='#a7a7a7').pack(anchor='w')
        ctk.CTkLabel(info, text=item.get('name', 'Playlist'), font=('Segoe UI', 28, 'bold'), wraplength=500, justify='left').pack(anchor='w')
        ctk.CTkLabel(info, text='Cargando canciones…', text_color='#a7a7a7').pack(anchor='w')
        def read():
            rows, offset = [], 0
            while True:
                response = playlist_items(sp, item['id'], limit=50, offset=offset)
                batch = response.get('items') or []
                rows.extend(batch)
                if not response.get('next') or not batch:
                    return rows
                offset += len(batch)
        def loaded(rows):
            if token != state['token']:
                return
            info.winfo_children()[-1].configure(text=f'{len(rows)} elementos')
            if not rows:
                ctk.CTkLabel(body, text='Esta playlist está vacía.').pack(pady=30)
            for index, row in enumerate(rows):
                track = (row or {}).get('item') or (row or {}).get('track') or {}
                line = ctk.CTkFrame(body, fg_color='#181818' if index % 2 == 0 else '#121212', corner_radius=6)
                line.pack(fill='x', pady=2)
                ctk.CTkLabel(line, text=str(index + 1), width=35, text_color='#a7a7a7').pack(side='left')
                # Cap downloads for large playlists; all rows remain visible.
                cover_label(line, image_url(track) if index < 40 else None, 44).pack(side='left', padx=8, pady=6)
                text = ctk.CTkFrame(line, fg_color='transparent')
                text.pack(side='left', fill='x', expand=True)
                ctk.CTkLabel(text, text=track.get('name', 'Contenido no disponible'), anchor='w', wraplength=450, justify='left').pack(fill='x')
                artist = ', '.join(a.get('name', '') for a in track.get('artists', [])) or (track.get('show') or {}).get('name', '')
                ctk.CTkLabel(text, text=artist, anchor='w', text_color='#a7a7a7', font=('Segoe UI', 11)).pack(fill='x')
                duration = track.get('duration_ms') or 0
                ctk.CTkLabel(line, text=f'{duration // 60000}:{duration // 1000 % 60:02}', text_color='#a7a7a7', width=60).pack(side='right', padx=10)
        run_job(frame, read, loaded, on_progress=progress.update_progress)

    def render(_=None):
        state['token'] += 1
        clear()
        columns=max(1,min(5,int(body.winfo_width()/frame._get_widget_scaling())//180))
        for column in range(5):
            body.grid_columnconfigure(column, weight=1 if column < columns else 0, uniform='covers' if column < columns else '')
        rows = [p for p in state['rows'] if query.get().casefold() in p.get('name', '').casefold()]
        if not rows:
            ctk.CTkLabel(body, text='No hay playlists para mostrar.').grid(row=0, column=0, columnspan=columns, pady=40)
        for index, item in enumerate(rows):
            card = ctk.CTkFrame(body, fg_color='#181818', corner_radius=10)
            card.grid(row=index // columns, column=index % columns, padx=6, pady=6, sticky='nsew')
            art = cover_label(card, image_url(item) if index < 40 else None, 140)
            art.pack(padx=12, pady=(12, 8))
            art.bind('<Button-1>', lambda _, p=item: detail(p))
            title=ctk.CTkLabel(card, text=item.get('name', 'Playlist'), anchor='w', wraplength=140, justify='left', font=('Segoe UI',13,'bold'))
            title.pack(fill='x',padx=14,pady=4)
            title.bind('<Button-1>',lambda _,p=item:detail(p))
            ctk.CTkButton(card, text='Abrir playlist', anchor='w', fg_color='transparent', hover_color='#282828', width=140, command=lambda p=item: detail(p)).pack(fill='x', padx=8)
            ctk.CTkLabel(card, text='Playlist · ' + (item.get('owner') or {}).get('display_name', 'Spotify'), text_color='#a7a7a7', font=('Segoe UI', 11), wraplength=140).pack(anchor='w', padx=14, pady=(0, 12))

    def refresh():
        def read():
            rows, offset = [], 0
            while True:
                response = current_user_playlists(sp, offset=offset)
                batch = response.get('items') or []
                rows.extend(p for p in batch if p)
                if not response.get('next') or not batch:
                    return rows
                offset += len(batch)
        def loaded(rows):
            state['rows'] = rows
            render()
        run_job(frame, read, loaded, controls=(refresh_button,), on_progress=progress.update_progress)
    ctk.CTkButton(toolbar, text='Biblioteca', width=100, fg_color='#282828', command=render).pack(side='left', padx=5)
    refresh_button = ctk.CTkButton(toolbar, text='Actualizar', width=100, command=refresh)
    refresh_button.pack(side='right')
    query.bind('<KeyRelease>', render)
    refresh()
    return frame
