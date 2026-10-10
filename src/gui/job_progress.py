import customtkinter as ctk


class JobProgress(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color='transparent')
        self.label = ctk.CTkLabel(self, text='Listo', anchor='w', wraplength=850)
        self.label.pack(fill='x')
        self.bar = ctk.CTkProgressBar(self)
        self.bar.pack(fill='x', pady=5)
        self.bar.set(0)

    def update_progress(self, done, total, message):
        self.bar.stop()
        if total:
            value = max(0, min(1, done / total))
            self.bar.configure(mode='determinate')
            self.bar.set(value)
            self.label.configure(text=f'{value:.0%} · {message}')
        else:
            self.bar.configure(mode='indeterminate')
            self.bar.start()
            self.label.configure(text=message)

    def finish(self, message='Completado'):
        self.update_progress(1, 1, message)

    def fail(self, error):
        self.bar.stop()
        self.label.configure(text=f'No se completó: {error}')
