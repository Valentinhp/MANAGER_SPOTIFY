import tkinter as tk
from tkinter import ttk, messagebox
from spotipy import Spotify
import json
import os
import threading
import logging
from ..utils.spotify_utils import obtener_canciones_artista, agregar_canciones_a_playlist

DATA_FILE = "SPOTYVMANAGER/SPOTYVMANAGER/src/data_assignments.json"

class VentanaSincronizarAsignaciones(ttk.Frame):
    def __init__(self, parent: ttk.Frame, sp: Spotify, **kwargs):
        super().__init__(parent, **kwargs)
        self.sp = sp
        self.sincronizando = False

        self.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Sincronizar Asignaciones", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, pady=(0, 20), sticky="w")

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        columns = ("artista", "playlist")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("artista", text="Artista")
        self.tree.heading("playlist", text="Playlist")
        self.tree.column("artista", width=300)
        self.tree.column("playlist", width=300)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Botones
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        btn_frame.columnconfigure(0, weight=1)

        self.btn_sincronizar = ttk.Button(btn_frame, text="Sincronizar Selección", command=self.sincronizar_seleccion_threaded)
        self.btn_sincronizar.grid(row=0, column=0, sticky="ew", padx=(0,5), ipady=4)
        
        self.btn_sinc_todos = ttk.Button(btn_frame, text="Sincronizar Todo", command=self.sincronizar_todo_threaded)
        self.btn_sinc_todos.grid(row=0, column=1, sticky="ew", padx=(5,0), ipady=4)

        self.cargar_asignaciones()

    def _set_buttons_state(self, state):
        self.btn_sincronizar.config(state=state)
        self.btn_sinc_todos.config(state=state)

    def cargar_asignaciones(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            if not os.path.exists(DATA_FILE):
                os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
                with open(DATA_FILE, "w") as f: json.dump([], f)

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                asignaciones = json.load(f)
                for asign in sorted(asignaciones, key=lambda x: x.get("artista_nombre", "")):
                    # Use a composite key for iid to ensure uniqueness
                    composite_iid = f'{asign["artista_id"]}|{asign["playlist_id"]}'
                    self.tree.insert("", tk.END, 
                                     values=(asign.get("artista_nombre", "N/A"), asign.get("playlist_nombre", "N/A")),
                                     iid=composite_iid)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.warning(f"No se pudo cargar el archivo de asignaciones: {e}")

    def _sincronizar_asignacion_worker(self, artista_id, playlist_id, artista_nombre):
        """Lógica de sincronización para un solo artista (para ser ejecutada en un hilo)."""
        try:
            logging.info(f"Sincronizando canciones de {artista_nombre}...")
            canciones_nuevas = obtener_canciones_artista(self.sp, artista_id)
            
            if canciones_nuevas is None: # Error de API manejado por el decorador
                self.winfo_toplevel().after(0, self._sincronizacion_finalizada, -1, artista_nombre)
                return

            if not canciones_nuevas:
                logging.info(f"No se encontraron canciones para {artista_nombre}.")
                self.winfo_toplevel().after(0, self._sincronizacion_finalizada, 0, artista_nombre)
                return

            res = agregar_canciones_a_playlist(self.sp, playlist_id, canciones_nuevas)
            self.winfo_toplevel().after(0, self._sincronizacion_finalizada, res, artista_nombre)

        except Exception as e:
            logging.error(f"Error al sincronizar {artista_nombre}: {e}")
            self.winfo_toplevel().after(0, self._sincronizacion_finalizada, -1, artista_nombre)

    def _sincronizacion_finalizada(self, res, artista_nombre):
        """Se ejecuta en el hilo principal al finalizar la sincronización de una selección."""
        self._set_buttons_state(tk.NORMAL)
        self.sincronizando = False
        if res > 0:
            messagebox.showinfo("Éxito", f"{res} canciones nuevas de {artista_nombre} añadidas.")
        elif res == 0:
            messagebox.showinfo("Sin Cambios", f"No hay canciones nuevas de {artista_nombre} para añadir.")
        else: # res < 0
            messagebox.showerror("Error", f"Ocurrió un error al sincronizar {artista_nombre}. Revisa el registro para más detalles.")

    def sincronizar_seleccion_threaded(self):
        if self.sincronizando:
            return
        selected_item_iid = self.tree.focus()
        if not selected_item_iid:
            messagebox.showerror("Error", "Selecciona una asignación para sincronizar.")
            return

        try:
            # Parse the composite iid
            artist_id, playlist_id = selected_item_iid.split('|')
        except ValueError:
            messagebox.showerror("Error", "La selección es inválida.")
            return

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                asignaciones = json.load(f)
            
            # Find the correct assignment using both IDs
            asign_sel = next((a for a in asignaciones if a["artista_id"] == artist_id and a["playlist_id"] == playlist_id), None)
            
            if not asign_sel: 
                messagebox.showerror("Error", "Asignación no encontrada en el archivo de datos.")
                return
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showerror("Error", "No se pudo leer el archivo de asignaciones.")
            return

        self.sincronizando = True
        self._set_buttons_state(tk.DISABLED)
        
        args = (asign_sel["artista_id"], asign_sel["playlist_id"], asign_sel["artista_nombre"])
        thread = threading.Thread(target=self._sincronizar_asignacion_worker, args=args)
        thread.daemon = True
        thread.start()

    def _sincronizar_todo_worker(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                asignaciones = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logging.warning("No hay asignaciones para sincronizar.")
            self.winfo_toplevel().after(0, self._sincronizacion_todo_finalizada, 0, [])
            return

        total_agregadas = 0
        errores = []
        for asign in asignaciones:
            logging.info(f"Sincronizando en lote: {asign['artista_nombre']}...")
            canciones_nuevas = obtener_canciones_artista(self.sp, asign["artista_id"])
            if canciones_nuevas is None:
                errores.append(asign["artista_nombre"])
                continue
            if not canciones_nuevas:
                continue
            
            res = agregar_canciones_a_playlist(self.sp, asign["playlist_id"], canciones_nuevas)
            if res is not None:
                if res > 0:
                    total_agregadas += res
                elif res < 0:
                    errores.append(asign["artista_nombre"])
        
        self.winfo_toplevel().after(0, self._sincronizacion_todo_finalizada, total_agregadas, errores)

    def _sincronizacion_todo_finalizada(self, total_agregadas, errores):
        self._set_buttons_state(tk.NORMAL)
        self.sincronizando = False
        msg_final = f"Sincronización completada. Se agregaron {total_agregadas} canciones en total."
        if errores:
            msg_final += "\n\nOcurrieron errores con los siguientes artistas:\n" + "\n".join(errores)
        
        messagebox.showinfo("Proceso Terminado", msg_final)

    def sincronizar_todo_threaded(self):
        if self.sincronizando:
            return
        if not messagebox.askyesno("Confirmar Sincronización Total", "Esto puede tardar un rato y realizar muchas peticiones a la API. ¿Continuar?"):
            return

        self.sincronizando = True
        self._set_buttons_state(tk.DISABLED)
        thread = threading.Thread(target=self._sincronizar_todo_worker)
        thread.daemon = True
        thread.start()
