import customtkinter as ctk
from tkinter import ttk,messagebox
from .async_tasks import run_job
from ..utils.spotify_utils import obtener_playlists_usuario,crear_playlist,unfollow_playlist,replace_playlist_items,remove_duplicates_from_playlist,obtener_contenido_playlist

def ventana_crear_playlist(parent,sp):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Crear playlist',font=('Segoe UI',24,'bold')).pack(pady=20)
    name=ctk.CTkEntry(frame,placeholder_text='Nombre de la playlist')
    name.pack(fill='x',padx=25,pady=10)
    def create():
        title=name.get().strip()
        if not title:return messagebox.showinfo('Nombre','Escribe un nombre.',parent=frame)
        run_job(frame,lambda:crear_playlist(sp,title),lambda pid:messagebox.showinfo('Creada',f'Playlist: {pid}',parent=frame),controls=(button,))
    button=ctk.CTkButton(frame,text='Crear playlist privada',command=create)
    button.pack(pady=15)
    return frame

def playlist_view(parent,sp,action='ver'):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text={'ver':'Mis playlists','vaciar':'Vaciar playlists','eliminar':'Dejar de seguir playlists','limpiar':'Limpiar duplicados'}[action],font=('Segoe UI',24,'bold')).pack(pady=15)
    query=ctk.CTkEntry(frame,placeholder_text='Filtrar por nombre')
    query.pack(fill='x',padx=15,pady=5)
    tree=ttk.Treeview(frame,columns=('name','count','id'),show='headings',selectmode='extended')
    for key,title in [('name','Nombre'),('count','Items'),('id','ID')]:tree.heading(key,text=title)
    tree.pack(fill='both',expand=True,padx=15,pady=10)
    details=ctk.CTkTextbox(frame,height=150)
    if action=='ver':details.pack(fill='x',padx=15,pady=5)
    rows=[]
    def render(_=None):
        tree.delete(*tree.get_children())
        text=query.get().casefold()
        for pid,name,count in rows:
            if text in name.casefold() and not tree.exists(pid):
                tree.insert('','end',iid=pid,values=(name,count,pid))
    def loaded(values):rows[:]=values;render()
    def refresh():run_job(frame,lambda:obtener_playlists_usuario(sp),loaded,controls=(refresh_button,))
    def operate():
        ids=list(tree.selection())
        if not ids:return messagebox.showinfo('Selección','Selecciona al menos una playlist.',parent=frame)
        if action!='ver' and not messagebox.askyesno('Confirmar',f'¿{action.capitalize()} {len(ids)} playlists seleccionadas?',parent=frame):return
        def work():
            result=[]
            for pid in ids:
                if action=='ver':result.extend(f'{title} — {artist}' for _,title,artist in obtener_contenido_playlist(sp,pid))
                elif action=='vaciar':replace_playlist_items(sp,pid,[]);result.append(f'{pid}: vaciada')
                elif action=='eliminar':unfollow_playlist(sp,pid);result.append(f'{pid}: dejaste de seguirla')
                else:
                    removed,remaining=remove_duplicates_from_playlist(sp,pid)
                    result.append(f'{pid}: {removed} duplicados eliminados; {remaining} items restantes')
            return result
        def done(result):
            if action=='ver':details.delete('1.0','end');details.insert('end','\n'.join(result) or 'Vacía')
            else:messagebox.showinfo('Completado','\n'.join(result),parent=frame);refresh()
        run_job(frame,work,done,controls=(button,refresh_button))
    bar=ctk.CTkFrame(frame)
    bar.pack(fill='x',padx=15,pady=10)
    button=ctk.CTkButton(bar,text='Ver contenido' if action=='ver' else 'Aplicar a seleccionadas',command=operate)
    button.pack(side='left',padx=5,pady=5)
    refresh_button=ctk.CTkButton(bar,text='Actualizar',command=refresh)
    refresh_button.pack(side='left',padx=5)
    query.bind('<KeyRelease>',render)
    refresh()
    return frame

def ventana_ver_playlists(parent,sp):return playlist_view(parent,sp,'ver')
def ventana_vaciar_playlists(parent,sp):return playlist_view(parent,sp,'vaciar')
def ventana_eliminar_playlists(parent,sp):return playlist_view(parent,sp,'eliminar')
def ventana_limpiar_playlists(parent,sp):return playlist_view(parent,sp,'limpiar')
