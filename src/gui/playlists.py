# src/gui/playlists.py
"""
Frames relacionados con Playlists.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from spotipy import Spotify
from ..utils.spotify_utils import (
    obtener_playlists_usuario,
    crear_playlist as api_crear_playlist,
    unfollow_playlist,
    replace_playlist_items,
    remove_duplicates_from_playlist,
)

# DEPRECATED: se conserva la implementaci?n original; usa la vista moderna.
def _legacy_ventana_ver_playlists(parent: ttk.Frame, sp: Spotify) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=10)
    
    cols = ("ID", "Nombre", "Tracks")
    tree = ttk.Treeview(frame, columns=cols, show="headings")
    for c in cols:
        tree.heading(c, text=c)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    for pid, nom, tot in obtener_playlists_usuario(sp):
        tree.insert("", tk.END, values=(pid, nom, tot))
        
    return frame

# DEPRECATED: se conserva la implementaci?n original; usa la vista moderna.
def _legacy_ventana_crear_playlist(parent: ttk.Frame, sp: Spotify) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=20)
    frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text="Nombre de la Playlist:").pack(pady=5)
    entry = ttk.Entry(frame, width=40)
    entry.pack(pady=5, fill="x", expand=True)

    def crear():
        nombre = entry.get().strip()
        if not nombre:
            messagebox.showwarning("Atención", "Ingresa un nombre")
            return
        try:
            pid = api_crear_playlist(sp, nombre)
            messagebox.showinfo("Completado", f"Playlist creada con ID: {pid}")
            # Podríamos querer cambiar de frame o refrescar algo aquí
            entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la playlist: {e}")

    ttk.Button(frame, text="Crear", command=crear).pack(pady=10)
    return frame

# DEPRECATED: se conserva la implementaci?n original; usa la vista moderna.
def _legacy_ventana_eliminar_playlists(parent: ttk.Frame, sp: Spotify) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=10)
    frame.rowconfigure(1, weight=1)
    frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text="Buscar playlists:", font=("Arial", 11)).pack(pady=(10, 0))
    entry_buscar = ttk.Entry(frame, width=50)
    entry_buscar.pack(pady=(0, 8), fill="x")

    pls = obtener_playlists_usuario(sp)
    filtered_pls = list(pls)

    list_frame = ttk.Frame(frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, bg="#2a2a2a", fg="white", selectbackground="#1DB954")
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scroll.set)

    def refrescar():
        listbox.delete(0, tk.END)
        for pid, nombre, _ in filtered_pls:
            listbox.insert(tk.END, f"{nombre}  ({pid[:12]}…)")

    def filtrar(_evt):
        term = entry_buscar.get().strip().lower()
        filtered_pls.clear()
        for item in pls:
            if term in item[1].lower():
                filtered_pls.append(item)
        refrescar()

    entry_buscar.bind("<KeyRelease>", filtrar)
    refrescar()

    def confirmar_elim():
        idxs = listbox.curselection()
        if not idxs:
            messagebox.showwarning("Atención", "No seleccionaste ninguna playlist.")
            return
        seleccion = [filtered_pls[i] for i in idxs]
        nombres = "\n".join(f"• {n}" for _, n, _ in seleccion)
        if not messagebox.askyesno("Confirmar eliminación", f"Vas a eliminar estas playlists:\n{nombres}\n\n¿Continuar?"):
            return
        errores = []
        for pid, nombre, _ in seleccion:
            if not unfollow_playlist(sp, pid):
                errores.append(nombre)
        
        if errores:
            messagebox.showerror("Errores", "Algunas no se pudieron eliminar:\n" + "\n".join(errores))
        else:
            messagebox.showinfo("¡Listo!", "Las playlists seleccionadas han sido eliminadas.")
        
        # Refrescar la lista original y la vista
        nonlocal pls
        pls = obtener_playlists_usuario(sp)
        filtrar(None)


    ttk.Button(frame, text="Eliminar seleccionadas", command=confirmar_elim).pack(pady=10)
    return frame

# DEPRECATED: se conserva la implementaci?n original; usa la vista moderna.
def _legacy_ventana_vaciar_playlists(parent: ttk.Frame, sp: Spotify) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=10)
    frame.rowconfigure(1, weight=1)
    frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text="Buscar playlists:", font=("Arial", 11)).pack(pady=(10, 0))
    entry_buscar = ttk.Entry(frame, width=50)
    entry_buscar.pack(pady=(0, 8), fill="x")

    todas = obtener_playlists_usuario(sp)
    mostradas = list(todas)

    list_frame = ttk.Frame(frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, bg="#2a2a2a", fg="white", selectbackground="#1DB954")
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scroll.set)

    def refrescar():
        listbox.delete(0, tk.END)
        for pid, nombre, _ in mostradas:
            listbox.insert(tk.END, f"{nombre}  ({pid[:12]}…)")

    def filtrar(_evt):
        texto = entry_buscar.get().strip().lower()
        mostradas.clear()
        for item in todas:
            if texto in item[1].lower():
                mostradas.append(item)
        refrescar()

    entry_buscar.bind("<KeyRelease>", filtrar)
    refrescar()

    def confirmar_vaciado():
        idxs = listbox.curselection()
        if not idxs:
            messagebox.showwarning("Atención", "No seleccionaste ninguna playlist.")
            return
        seleccion = [mostradas[i] for i in idxs]
        nombres = "\n".join(f"• {n}" for _, n, _ in seleccion)
        if not messagebox.askyesno("Confirmar vaciado", f"Vas a vaciar estas playlists:\n{nombres}\n\n¿Continuar?"):
            return
        errores = []
        for pid, nombre, _ in seleccion:
            if not replace_playlist_items(sp, pid, []):
                errores.append(nombre)
        if errores:
            messagebox.showerror("Errores", "Errores al vaciar:\n" + "\n".join(errores))
        else:
            messagebox.showinfo("¡Hecho!", "Las playlists seleccionadas han quedado vacías.")

    ttk.Button(frame, text="Vaciar seleccionadas", command=confirmar_vaciado).pack(pady=10)
    return frame

# DEPRECATED: se conserva la implementaci?n original; usa la vista moderna.
def _legacy_ventana_limpiar_playlists(parent: ttk.Frame, sp: Spotify) -> ttk.Frame:
    frame = ttk.Frame(parent, padding=10)
    frame.rowconfigure(1, weight=1)
    frame.columnconfigure(0, weight=1)

    ttk.Label(frame, text="Buscar playlists:", font=("Arial", 11)).pack(pady=(10, 0))
    entry_buscar = ttk.Entry(frame, width=50)
    entry_buscar.pack(pady=(0, 8), fill="x")

    todas = obtener_playlists_usuario(sp)
    mostradas = list(todas)

    list_frame = ttk.Frame(frame)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, bg="#2a2a2a", fg="white", selectbackground="#1DB954")
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.config(yscrollcommand=scroll.set)

    def refrescar():
        listbox.delete(0, tk.END)
        for pid, nombre, _ in mostradas:
            listbox.insert(tk.END, f"{nombre}  ({pid[:12]}…)")

    def filtrar(_evt):
        texto = entry_buscar.get().strip().lower()
        mostradas.clear()
        for item in todas:
            if texto in item[1].lower():
                mostradas.append(item)
        refrescar()

    entry_buscar.bind("<KeyRelease>", filtrar)
    refrescar()

    def confirmar_limpieza():
        idxs = listbox.curselection()
        if not idxs:
            messagebox.showwarning("Atención", "No seleccionaste ninguna playlist.")
            return
        seleccion = [mostradas[i] for i in idxs]
        nombres = "\n".join(f"• {n}" for _, n, _ in seleccion)
        if not messagebox.askyesno("Confirmar limpieza", f"Vas a limpiar estas playlists:\n{nombres}\n\nSe eliminarán las canciones duplicadas. ¿Continuar?"):
            return
        
        resultados = []
        errores = []
        for pid, nombre, _ in seleccion:
            try:
                eliminados, restantes = remove_duplicates_from_playlist(sp, pid)
                if eliminados > 0:
                    resultados.append(f"• {nombre}: {eliminados} duplicados eliminados. Quedan {restantes} canciones.")
                else:
                    resultados.append(f"• {nombre}: No se encontraron duplicados.")
            except Exception as e:
                errores.append(f"• {nombre}: {e}")

        msg_final = ""
        if resultados:
            msg_final += "Limpieza completada:\n" + "\n".join(resultados)
        if errores:
            msg_final += "\n\nErrores:\n" + "\n".join(errores)
        
        messagebox.showinfo("Resultado de la limpieza", msg_final)

    ttk.Button(frame, text="Limpiar seleccionadas (eliminar duplicados)", command=confirmar_limpieza).pack(pady=10)
    return frame


def ventana_ver_playlists(parent, sp):
    from .modern_playlists import ventana_ver_playlists as modern
    return modern(parent, sp)


def ventana_crear_playlist(parent, sp):
    from .modern_playlists import ventana_crear_playlist as modern
    return modern(parent, sp)


def ventana_vaciar_playlists(parent, sp):
    from .modern_playlists import ventana_vaciar_playlists as modern
    return modern(parent, sp)


def ventana_eliminar_playlists(parent, sp):
    from .modern_playlists import ventana_eliminar_playlists as modern
    return modern(parent, sp)


def ventana_limpiar_playlists(parent, sp):
    from .modern_playlists import ventana_limpiar_playlists as modern
    return modern(parent, sp)
