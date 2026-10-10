"""Los workers solo escriben en Queue; Tk se actualiza desde el hilo principal."""
import queue
import threading
from tkinter import messagebox
from ..utils.progress import progress_reporter

def run_job(frame, work, on_success, on_error=None, controls=(), on_progress=None):
    root = frame.winfo_toplevel()
    results = queue.Queue()
    for control in controls:
        control.configure(state='disabled')
    if hasattr(root, 'job_started'):
        root.job_started()

    def worker():
        try:
            with progress_reporter(lambda done, total, text: results.put(('progress', (done, total, text)))):
                value = work()
            results.put((True, value))
        except Exception as error:
            results.put((False, error))

    def poll():
        latest = None
        completed = None
        for _ in range(100):
            try:
                success, value = results.get_nowait()
            except queue.Empty:
                break
            if success == 'progress':
                latest = value
            else:
                completed = (success, value)
                break
        if latest is not None:
            if hasattr(root, 'job_progress'):
                root.job_progress(*latest)
            if frame.winfo_exists() and on_progress:
                on_progress(*latest)
        if completed is None:
            root.after(75, poll)
            return
        success, value = completed
        if hasattr(root, 'job_finished'):
            root.job_finished()
        if not frame.winfo_exists():
            return
        if on_progress:
            on_progress(1 if success else 0, 1, 'Completado' if success else f'No se completó: {value}')
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
