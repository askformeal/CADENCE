import tkinter as tk

class ScrolledFrame(tk.Frame):
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)

        self.scroll_on = False

        scroll_bar = tk.Scrollbar(self, orient='vertical')
        scroll_bar.pack(side='right', fill='y')

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)


        self.frame = tk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.frame, anchor='nw')

        scroll_bar.config(command=self.canvas.yview)
        self.canvas.config(yscrollcommand=scroll_bar.set)

        self.frame.bind('<Configure>', self._on_frame_config)
        self.canvas.bind('<Configure>', self._on_canvas_config)

        self.bind('<Enter>', lambda *_: self._set_scroll(True))
        self.bind('<Leave>', lambda *_: self._set_scroll(False))

        self.bind_all('<MouseWheel>', self._on_scroll)
        self.bind_all('<Button-5>', self._on_scroll)
        self.bind_all('<Button-4>', self._on_scroll)

    def yview(self):
        return self.canvas.yview()

    def yview_moveto(self, fraction):
        self.canvas.yview_moveto(fraction)
        self._on_frame_config()

    def clear(self):
        for child in self.frame.winfo_children():
            child.destroy()
        self.yview_moveto(0)

    def _set_scroll(self, scroll):
        self.scroll_on = scroll

    def _on_frame_config(self, *_):
        self.canvas.config(scrollregion=self.canvas.bbox('all'))

    def _on_canvas_config(self, event):
        self.canvas.itemconfig(self.window, width=event.width)

    def _on_scroll(self, event):
        if self.scroll_on:
            if event.num == 4:
                step = -1
            elif event.num == 5:
                step = 1
            elif event.delta > 0:
                step = -1
            else:
                step = 1

            self.canvas.yview_scroll(step, 'units')
