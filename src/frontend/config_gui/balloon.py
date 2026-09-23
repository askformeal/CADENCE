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
            x = widget.winfo_rootx() + widget.winfo_width() + BALLOON_OFFSET_X
            y = widget.winfo_rooty() + widget.winfo_height() + BALLOON_OFFSET_Y
        except tk.TclError:
            ...
        else:
            self.label.config(text=text)
            self.update_idletasks()

            if x + self.winfo_reqwidth() > self.winfo_screenwidth():
                x = widget.winfo_rootx() - self.winfo_reqwidth() - BALLOON_OFFSET_X
                x = max(0, x)

            if y + self.winfo_reqheight() > self.winfo_screenheight():
                y = widget.winfo_rooty() - self.winfo_reqheight() - BALLOON_OFFSET_Y
                y = max(0, y)

            self.geometry(f'+{x}+{y}')
            self.deiconify()

    def bind_widget(self, widget, text):
        logger.debug(f'bind {text} to {widget}')
        widget.bind('<Enter>', lambda *_: self._on_enter(widget, text))
        widget.bind('<Leave>', lambda *_: self._on_leave())
