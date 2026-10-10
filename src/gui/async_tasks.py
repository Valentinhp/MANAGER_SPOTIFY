"""Los workers solo escriben en Queue; Tk se actualiza desde el hilo principal."""
import queue
import threading
from tkinter import messagebox

def run_job(frame, work, on_success, on_error=None, controls=()):
    root = frame.winfo_toplevel()
    results = queue.Queue()
    for control in controls:
        control.configure(state='disabled')
    if hasattr(root, 'job_started'):
        root.job_started()

    def worker():
        try:
            results.put((True, work()))
        except Exception as error:
            results.put((False, error))

    def poll():
        try:
            success, value = results.get_nowait()
        except queue.Empty:
            root.after(75, poll)
            return
        if hasattr(root, 'job_finished'):
            root.job_finished()
        if not frame.winfo_exists():
            return
        for control in controls:
            if control.winfo_exists():
                control.configure(state='normal')
        if success:
            on_success(value)
        elif on_error:
            on_error(value)
        else:
            messagebox.showerror('No se pudo completar', str(value), parent=root)

    threading.Thread(target=worker, daemon=True).start()
    root.after(75, poll)
