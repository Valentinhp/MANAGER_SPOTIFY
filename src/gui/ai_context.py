from datetime import datetime
import customtkinter as ctk
from .ai_mood import ventana_ai_mood

def ventana_ai_context(parent, sp):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Playlist por hora y clima',font=('Segoe UI',24,'bold')).pack(pady=25)
    prompt=ctk.CTkEntry(frame,placeholder_text='Actividad o ánimo: caminar, trabajar, descansar…',width=600)
    prompt.pack(padx=20,pady=15,fill='x')
    weather=ctk.CTkEntry(frame,placeholder_text='Clima opcional: lluvia ligera, calor, tarde nublada…')
    weather.pack(padx=20,pady=15,fill='x')
    def generate():
        text=f'{prompt.get() or "Música para este momento"}. Hora local: {datetime.now().strftime("%H:%M")}. Clima: {weather.get() or "sin especificar"}.'
        frame.winfo_toplevel().show_frame(lambda p,s:ventana_ai_mood(p,s,initial_prompt=text))
    ctk.CTkButton(frame,text='Preparar Radio de Ánimo',command=generate).pack(pady=20)
    return frame
