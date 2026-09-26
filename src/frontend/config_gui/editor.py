import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser

from src.constants.config_gui import (
    FONT_SIZE,
    ON_COLOR_BG,
    ON_COLOR_FG,
    OFF_COLOR_BG,
    OFF_COLOR_FG,
    )
from src.utils.misc import squeeze, hex_color_gray

class EditorMixin:
    def build_bool_editor(self, value_frame):
        switch = tk.Button(
            value_frame,
            font=self.font,
            command=lambda *_: self._toggle_switch(switch)
            )
        switch.pack(side='right', padx=(20, 10))
        self.switch_on = self.value
        self._apply_switch(switch)
        self.get_val = self._get_switch
        
    def build_choice_editor(self, value_frame):
        var = tk.StringVar()
        menu = tk.OptionMenu(
            value_frame,
            var,
            *self.choices
        )
        menu.pack(side='right', padx=(20, 10))
        var.set(self.value)
        self.get_val = var.get
        
    def build_percent_editor(self, value_frame):
        scale_font = tkfont.Font(
            size=FONT_SIZE-3,
            slant='italic',
        )
        scale = tk.Scale(
            value_frame,
            font=scale_font,
            length=200,
            from_=0,
            to=100,
            tickinterval=25,
            orient='horizontal',
        )
        scale.pack(side='right', padx=(0, 5))
        
        self.bind('<Left>', lambda *_: self._nudge_scale(scale, -1))
        self.bind('<Right>', lambda *_: self._nudge_scale(scale, 1))
        self.bind('<Control-Left>', lambda *_: self._nudge_scale(scale, -5))
        self.bind('<Control-Right>', lambda *_: self._nudge_scale(scale, 5))
        self.bind('<Shift-Left>', lambda *_: self._nudge_scale(scale, -20))
        self.bind('<Shift-Right>', lambda *_: self._nudge_scale(scale, 20))
        
        scale.set(self.value)
        self.get_val = lambda: str(scale.get())

    def build_color_editor(self, value_frame):
        entry = tk.Entry(
            value_frame, 
            font=self.font,
            relief='raised'
            )

        button = tk.Button(
            value_frame,
            )
        button.config(command=lambda: self._get_color(entry, button))
        
        button.pack(side='right', padx=(0, 5))
        entry.pack(side='right', padx=(0, 5))

        entry.insert(0, str(self.value))
        self._update_color_button(self.value, button)
        
        self.get_val = entry.get

    def build_entry_editor(self, value_frame):
        entry = tk.Entry(
            value_frame, 
            font=self.font,
            relief='raised'
            )
        entry.pack(side='right', padx=(20, 10))
        entry.insert(tk.END, str(self.value))
        self.get_val = entry.get

    def _toggle_switch(self, switch):
        self.switch_on = not self.switch_on
        self._apply_switch(switch)

    def _apply_switch(self, switch):
        if self.switch_on:
            switch.config(
                text='On', 
                bg=ON_COLOR_BG,
                fg=ON_COLOR_FG
                )
        else:
            switch.config(
                text='Off',
                bg=OFF_COLOR_BG,
                fg=OFF_COLOR_FG
                )

    def _get_switch(self):
        return str(self.switch_on)

    def _nudge_scale(self, scale, step):
        number = scale.get()
        scale.set(squeeze(number + step, 100, 0))

    def _get_color(self, entry, button):
        color = colorchooser.askcolor(parent=self)[1]
        if color is not None:
            entry.delete(0, tk.END)
            entry.insert(0, color)
            self._update_color_button(color, button)

    def _update_color_button(self, color, button):
        button.config(bg=color)
        button.config(activebackground=color)
        gray = hex_color_gray(color)
        if gray > 128:
            button.config(image=self.master.color_black_image)
        else:
            button.config(image=self.master.color_white_image)
