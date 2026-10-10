"""Conexión voluntaria al plan de ChatGPT y selección de cuenta/modelo."""
import webbrowser
import customtkinter as ctk
from tkinter import messagebox
from .async_tasks import run_job
from ..config import AI_PROVIDER
from ..utils import chatgpt_session as session


def chatgpt_controls(parent):
    box = ctk.CTkFrame(parent)
    box.grid_columnconfigure(0, weight=1)
    status = ctk.CTkLabel(box, text='Conecta tu plan de ChatGPT una vez; después la IA funciona automáticamente.', anchor='w', wraplength=650)
    status.grid(row=0, column=0, columnspan=4, padx=10, pady=5, sticky='ew')
    controls = []
    labels, models = {}, {}
    account = ctk.CTkOptionMenu(box, values=['Sin cuenta'], width=200)
    account.grid(row=1, column=0, padx=5, pady=5, sticky='w')
    model = ctk.CTkOptionMenu(box, values=['Modelo automático'], width=170)
    model.grid(row=1, column=1, padx=5, pady=5)

    def refresh_accounts():
        try:
            profiles, active = session.accounts()
        except session.ChatGPTError as error:
            status.configure(text=str(error)); return
        labels.clear()
        labels.update((p['label'], p['id']) for p in profiles)
        account.configure(values=list(labels) or ['Sin cuenta'])
        selected = next((p for p in profiles if p['id'] == active), None)
        account.set(selected['label'] if selected else next(iter(labels), 'Sin cuenta'))
        if AI_PROVIDER == 'openai':
            status.configure(text='Modo API de OpenAI: facturación separada. Para usar tu plan, configura AI_PROVIDER=chatgpt y reinicia.')
        elif selected and selected['connected'] and selected['enabled']:
            status.configure(text='Usando tu plan de ChatGPT · ' + selected['label'])
        elif selected and selected['connected']:
            status.configure(text='Cuenta conectada. Pulsa Continue with ChatGPT y permite usar tu plan.')
        else:
            status.configure(text='Conecta tu plan de ChatGPT una vez; después la IA funciona automáticamente.')

    def models_loaded(values):
        values, selected = values
        models.clear()
        models.update((item.get('display_name', item['slug']), item['slug']) for item in values)
        model.configure(values=list(models))
        model.set(next(label for label, slug in models.items() if slug == selected))
        refresh_accounts()

    def load_models():
        model.set('Consultando modelos…')
        def work():
            values = session.available_models()
            selected = session.model_preference()
            if not any(item['slug'] == selected for item in values):
                selected = values[0]['slug']
            session.select_model(selected)
            return values, selected
        run_job(box, work, models_loaded, controls=controls)

    def connected(profile):
        refresh_accounts()
        if profile['enabled']:
            load_models()
        else:
            messagebox.showinfo('Permiso del plan', 'La cuenta se conectó, pero no autorizaste el uso del plan. Puedes permitirlo al reconectar.', parent=box)

    def connect(new=False):
        selected = labels.get(account.get())
        status.configure(text='Completa el inicio de sesión y permite el uso del plan en el navegador…')
        run_job(box, lambda: session.connect(selected, new=new), connected, controls=controls)

    def choose_account(label):
        if label not in labels:
            return
        selected = labels[label]
        def done(_):
            refresh_accounts()
            models.clear(); model.configure(values=['Modelo automático']); model.set('Modelo automático')
        run_job(box, lambda: session.select_account(selected), done, controls=controls)

    def choose_model(label):
        if label in models:
            selected = models[label]
            run_job(box, lambda: session.select_model(selected), lambda _: None, controls=controls)

    def disconnected(confirmed):
        refresh_accounts()
        model.set('Modelo automático')
        if not confirmed:
            messagebox.showinfo('Sesión cerrada', 'Se cerró la sesión local. No se pudo confirmar la desconexión remota; revoca el acceso desde la configuración de ChatGPT.', parent=box)

    account.configure(command=choose_account)
    model.configure(command=choose_model)
    button = ctk.CTkButton(box, text='Continue with ChatGPT', command=connect, width=175)
    button.grid(row=1, column=2, padx=5, pady=5)
    more = ctk.CTkOptionMenu(box, values=['Opciones', 'Añadir cuenta', 'Actualizar modelos', 'Cerrar sesión', 'Ver uso del plan'], width=120)
    def option(value):
        more.set('Opciones')
        if value == 'Añadir cuenta':
            connect(new=True)
        elif value == 'Actualizar modelos':
            load_models()
        elif value == 'Cerrar sesión':
            run_job(box, session.disconnect, disconnected, controls=controls)
        elif value == 'Ver uso del plan':
            webbrowser.open('https://chatgpt.com/settings/usage')
    more.configure(command=option)
    more.grid(row=1, column=3, padx=5, pady=5)
    controls.extend((account, model, button, more))
    refresh_accounts()
    return box
