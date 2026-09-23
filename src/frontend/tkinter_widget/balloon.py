import tkinter as tk

class Balloon(tk.Toplevel):
    def __init__(self, *args, wrap_len=0, offset_x=0, offset_y=0, windup=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.windup = windup

        self.withdraw()
        self.overrideredirect(True)
        self.attributes('-topmost', True)

        self.label = tk.Label(
            self, 
            bg=self.cget('background'),
            wraplength=wrap_len,
            relief='solid',
            bd=1
            )
        self.label.pack()

        self.job = None

    def _on_enter(self, widget, text):
        self.job = self.after(
            self.windup, 
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
        try:
            x = widget.winfo_rootx() + widget.winfo_width() + self.offset_x
            y = widget.winfo_rooty() + widget.winfo_height() + self.offset_y
        except tk.TclError:
            ...
        else:
            self.label.config(text=text)
            self.update_idletasks()

            if x + self.winfo_reqwidth() > self.winfo_screenwidth():
                x = widget.winfo_rootx() - self.winfo_reqwidth() - self.offset_x
                x = max(0, x)

            if y + self.winfo_reqheight() > self.winfo_screenheight():
                y = widget.winfo_rooty() - self.winfo_reqheight() - self.offset_y
                y = max(0, y)

            self.geometry(f'+{x}+{y}')
            self.deiconify()

    def bind_widget(self, widget, text):
        widget.bind('<Enter>', lambda *_: self._on_enter(widget, text))
        widget.bind('<Leave>', lambda *_: self._on_leave())
