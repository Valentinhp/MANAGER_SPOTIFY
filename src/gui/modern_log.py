import customtkinter as ctk
from .gui_handler import gui_handler

def ventana_log_viewer(parent,sp):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Registro de la aplicación',font=('Segoe UI',24,'bold')).pack(pady=15)
    text=ctk.CTkTextbox(frame)
    text.pack(fill='both',expand=True,padx=15,pady=10)
    gui_handler.set_widget(text)
    return frame
