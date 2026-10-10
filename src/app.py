"""
Lanza la aplicación completa
"""
import logging
import sys
from .auth import get_spotify_client
from .gui.main_window import build_main_window
from .gui.gui_handler import gui_handler

def main(smoke=False) -> None:
    # --- Configure Logging ---
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add our GUI handler
    gui_handler.setFormatter(formatter)
    root_logger.addHandler(gui_handler)

    # Add a console handler to show logs in the terminal
    if sys.stdout is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    from .config import APP_DIR, DATA_DIR
    log_dir = (DATA_DIR.parent if getattr(sys, 'frozen', False) else APP_DIR) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(log_dir / 'app.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.info("Iniciando SpotyVManager...")

    if smoke:
        from unittest.mock import Mock
        sp = Mock()
    else:
        try:
            sp = get_spotify_client()
        except ValueError as error:
            import customtkinter as ctk
            from tkinter import messagebox
            dialog_root = ctk.CTk()
            dialog_root.withdraw()
            messagebox.showerror('Configuración requerida', str(error), parent=dialog_root)
            dialog_root.destroy()
            return
    root = build_main_window(sp, smoke=smoke)
    if smoke:
        root.after(1000, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    main(smoke='--smoke' in sys.argv)
