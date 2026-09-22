import tkinter as tk

from src.constants.config_gui import (
    BALLOON_BG, 
    BALLOON_WRAP,
    BALLOON_OFFSET_X,
    BALLOON_OFFSET_Y,
    BALLOON_WINDUP
    )
from .logger import logger

class Balloon(tk.Toplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.withdraw()
        self.overrideredirect(True)
        self.attributes('-topmost', True)

        self.label = tk.Label(
            self, 
            bg=BALLOON_BG,
            wraplength=BALLOON_WRAP,
            relief='solid',
            bd=1
            )
        self.label.pack()

        self.job = None

    def _on_enter(self, widget, text):
        self.job = self.after(
            BALLOON_WINDUP, 
            self._show, 
            widget=widget, 
            text=text
            )

    def _on_leave(self):
        if self.job is not None:
            self.after_cancel(self.job)
            self.job = None
        self.withdraw()

    def _show(self, widget, text):
        logger.debug(f'Show balloon \"{text}\" for {widget}')
        try:
            x = widget.winfo_rootx() + widget.winfo_width()
            y = widget.winfo_rooty() + widget.winfo_height()
        except tk.TclError:
            ...
        else:
            self.label.config(text=text)
            self.update_idletasks()
            self.geometry(f'+{x+BALLOON_OFFSET_X}+{y+BALLOON_OFFSET_Y}')
            self.deiconify()

    def bind_widget(self, widget, text):
        logger.debug(f'bind {text} to {widget}')
        widget.bind('<Enter>', lambda *_: self._on_enter(widget, text))
        widget.bind('<Leave>', lambda *_: self._on_leave())
