"""Task-based navigation retaining the existing screens."""
import customtkinter as ctk
from .visual_library import ventana_biblioteca


def section(parent, sp, pages):
    frame = ctk.CTkFrame(parent, fg_color='#121212', corner_radius=12)
    bar = ctk.CTkScrollableFrame(frame, orientation='horizontal', height=44, fg_color='transparent')
    bar.pack(fill='x', padx=15, pady=(12, 0))
    content = ctk.CTkFrame(frame, fg_color='transparent')
    content.pack(fill='both', expand=True)
    state = {'page': None}
    buttons = []
    def show(index):
        if state['page'] is not None:
            state['page'].destroy()
        for i, button in enumerate(buttons):
            button.configure(fg_color='#333333' if i == index else 'transparent')
        state['page'] = pages[index][1](content, sp)
        state['page'].pack(fill='both', expand=True)
    for index, (label, _) in enumerate(pages):
        button = ctk.CTkButton(bar, text=label, width=110, height=32, corner_radius=16,
                              fg_color='transparent', hover_color='#333333', command=lambda i=index: show(i))
        button.pack(side='left', padx=3)
        buttons.append(button)
    show(0)
    return frame


def settings(parent, sp):
    from .chatgpt_controls import chatgpt_controls
    frame = ctk.CTkFrame(parent, fg_color='#121212')
    ctk.CTkLabel(frame, text='Configuración', font=('Segoe UI', 30, 'bold')).pack(anchor='w', padx=25, pady=25)
    ctk.CTkLabel(frame, text='Cuenta y modelo de ChatGPT', text_color='#a7a7a7').pack(anchor='w', padx=25)
    chatgpt_controls(frame).pack(fill='x', padx=25, pady=15)
    ctk.CTkLabel(frame, text='Spotify utiliza la configuración de tu archivo .env.\nReinicia la aplicación después de modificarla.', justify='left', text_color='#a7a7a7').pack(anchor='w', padx=25, pady=20)
    return frame
