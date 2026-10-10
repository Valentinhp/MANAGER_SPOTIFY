import webbrowser
import customtkinter as ctk
from tkinter import ttk
from .async_tasks import run_job
from ..utils.ai_history import load_history

def ventana_ai_history(parent, sp):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Historial local de IA',font=('Segoe UI',24,'bold')).pack(pady=15)
    tree=ttk.Treeview(frame,columns=('date','prompt','count','playlist'),show='headings')
    for column,label in [('date','Fecha'),('prompt','Solicitud'),('count','Canciones'),('playlist','Playlist')]:tree.heading(column,text=label)
    tree.pack(fill='both',expand=True,padx=15,pady=10)
    detail=ctk.CTkTextbox(frame,height=170)
    detail.pack(fill='x',padx=15,pady=5)
    entries=[]
    def show(rows):
        entries[:]=rows[::-1]
        tree.delete(*tree.get_children())
        for i,row in enumerate(entries):tree.insert('','end',iid=str(i),values=(row['date'],row['prompt'],len(row['songs']),row.get('playlist_id') or 'Sin crear'))
    def select(_):
        if tree.selection():
            row=entries[int(tree.selection()[0])]
            detail.delete('1.0','end')
            detail.insert('end','\n'.join(f'{song["title"]} — {song["artist"]}' for song in row['songs']))
    def open_playlist():
        if tree.selection():
            pid=entries[int(tree.selection()[0])].get('playlist_id')
            if pid:webbrowser.open(f'https://open.spotify.com/playlist/{pid}')
    ctk.CTkButton(frame,text='Abrir playlist en Spotify',command=open_playlist).pack(pady=10)
    ctk.CTkButton(frame,text='Actualizar',command=lambda:run_job(frame,load_history,show)).pack(pady=5)
    tree.bind('<<TreeviewSelect>>',select)
    run_job(frame,load_history,show)
    return frame
