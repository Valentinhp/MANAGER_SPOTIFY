import logging
import tkinter as tk
from collections import deque

class GuiLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.text_widget = None
        self.message_queue = deque(maxlen=1000)

    def set_widget(self, text_widget):
        self.text_widget = text_widget
        if self.text_widget:
            self.text_widget.configure(state=tk.NORMAL)
            while self.message_queue:
                self.text_widget.insert(tk.END, self.message_queue.popleft())
            self.text_widget.configure(state=tk.DISABLED)
            if self.message_queue:
                 self.text_widget.see(tk.END)

    def emit(self, record):
        msg = self.format(record) + "\n"
        if self.text_widget:
            self.text_widget.configure(state=tk.NORMAL)
            self.text_widget.insert(tk.END, msg)
            self.text_widget.configure(state=tk.DISABLED)
            self.text_widget.see(tk.END)
        else:
            self.message_queue.append(msg)

gui_handler = GuiLogHandler()