import logging
import tkinter as tk
import queue
from collections import deque

class GuiLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.text_widget = None
        self.message_queue = queue.Queue(maxsize=1000)
        self.history = deque(maxlen=1000)
        self._polling = False

    def set_widget(self, text_widget):
        self.text_widget = text_widget
        if text_widget and text_widget.winfo_exists():
            text_widget.configure(state=tk.NORMAL)
            text_widget.delete('1.0', tk.END)
            text_widget.insert(tk.END, ''.join(self.history))
            text_widget.configure(state=tk.DISABLED)
            if not self._polling:
                self._polling = True
                self._drain()

    def _drain(self):
        widget = self.text_widget
        if not widget or not widget.winfo_exists():
            self._polling = False
            return
        messages = []
        while True:
            try: messages.append(self.message_queue.get_nowait())
            except queue.Empty: break
        if messages:
            self.history.extend(messages)
            widget.configure(state=tk.NORMAL)
            widget.insert(tk.END, ''.join(messages))
            widget.configure(state=tk.DISABLED)
            widget.see(tk.END)
        widget.after(100, self._drain)

    def emit(self, record):
        message = self.format(record) + '\n'
        try: self.message_queue.put_nowait(message)
        except queue.Full:
            try: self.message_queue.get_nowait()
            except queue.Empty: pass
            try: self.message_queue.put_nowait(message)
            except queue.Full: pass

gui_handler = GuiLogHandler()
