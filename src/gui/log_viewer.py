import tkinter as tk
from tkinter import ttk
from spotipy import Spotify
from .gui_handler import gui_handler

class LogViewer(ttk.Frame):
    def __init__(self, parent: ttk.Frame, sp: Spotify, **kwargs):
        super().__init__(parent, style="Content.TFrame", **kwargs)
        
        self.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        ttk.Label(self, text="Registro de Actividad", style="Sub.TLabel").pack(anchor="w", pady=(0, 15))
        
        text_frame = ttk.Frame(self, style="Content.TFrame")
        text_frame.pack(expand=True, fill=tk.BOTH)
        
        log_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED, 
            bg="#1c1c1c",
            fg="#e0e0e0", 
            font=("Consolas", 10), 
            relief=tk.SOLID, 
            borderwidth=1,
            highlightthickness=0
        )
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=log_text.yview)
        log_text.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.pack(expand=True, fill=tk.BOTH)
        
        gui_handler.set_widget(log_text)

        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, event):
        if event.widget == self:
            gui_handler.set_widget(None)

def ventana_log_viewer(parent, sp):
    """Factory function to create a LogViewer instance."""
    return LogViewer(parent, sp)