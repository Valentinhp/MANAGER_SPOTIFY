"""
Lanza la aplicación completa
"""
import logging
import sys
from .auth import get_spotify_client
from .gui.main_window import build_main_window
from .gui.gui_handler import gui_handler

def main() -> None:
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
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    logging.info("Iniciando SpotyVManager...")

    sp = get_spotify_client()
    root = build_main_window(sp)
    root.mainloop()

if __name__ == "__main__":
    main()