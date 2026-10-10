import customtkinter as ctk
from tkinter import messagebox
from .async_tasks import run_job
from ..utils.ai_recommender import resumir_gusto

def ventana_ai_profile(parent, sp):
    frame=ctk.CTkFrame(parent)
    ctk.CTkLabel(frame,text='Resumen de tu gusto',font=('Segoe UI',24,'bold')).pack(pady=15)
    ctk.CTkLabel(frame,text='Describe tus gustos con tus propias palabras. Solo este texto se envía a Claude.').pack(padx=20,pady=10)
    entry=ctk.CTkTextbox(frame,height=140)
    entry.pack(fill='x',padx=20,pady=10)
    result=ctk.CTkTextbox(frame)
    result.pack(fill='both',expand=True,padx=20,pady=10)
    def done(text):
        result.delete('1.0','end');result.insert('end',text)
    def generate():
        text=entry.get('1.0','end').strip()
        if not text:return messagebox.showinfo('Tus gustos','Describe qué música te gusta.',parent=frame)
        run_job(frame,lambda:resumir_gusto(text),done,controls=(button,))
    button=ctk.CTkButton(frame,text='Crear perfil divertido',command=generate)
    button.pack(pady=15)
    return frame
