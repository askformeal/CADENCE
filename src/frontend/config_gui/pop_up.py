import tkinter as tk
import tkinter.font as tkfont

from .logger import logger
from src.constants.paths import ICON_PATH
from src.constants.config_gui import (
    POP_UP_POS_X, 
    POP_UP_POS_Y, 
    TYPE_WRAP_LEN,
    DESC_WRAP_LEN,
    FONT_SIZE,
    CONFIRM_COLOR,
    CANCEL_COLOR,
    UNSET_COLOR
    )
from .editor import EditorMixin

class Popup(tk.Toplevel, EditorMixin):
    def __init__(self, master, info):
        super().__init__(master=master)
        self.withdraw()

        self.set_value = master.set_value
        self.unset_option = master.unset
        self.balloon = master.balloon

        self.name = info['name']
        self.value = info['value']
        self.type_ = info['type']
        self.type_raw = info['type_raw']
        self.source = info['source']
        self.choices = info['choices']
        self.desc = info['description']

        self.switch_on = False

        self.title(f'Edit \"{self.name}\"')
        x = master.winfo_x() + POP_UP_POS_X
        y = master.winfo_y() + POP_UP_POS_Y
        self.geometry(f'+{x}+{y}')
        self.resizable(False, False)
        self.iconbitmap(ICON_PATH)
        self.bind('<Escape>', lambda *_: self.destroy())
        self.bind('<Return>', lambda *_: self._on_confirm(force=False))
        self.bind('<Delete>', self._unset)

        self.transient(self.master)
        self.grab_set()
        self.focus_set()

        self._build_window()
        self.deiconify()
        logger.debug('Pop-up Window pop up')

    def _build_window(self):
        self.font = tkfont.Font(
            size=FONT_SIZE,
        )

        self.main_frame = tk.Frame(self)
        self.main_frame.pack(padx=5, pady=5)

        self._build_name()
        self._build_value()
        self._build_source()
        self._build_type()
        self._build_desc()
        self._build_buttons()

        logger.debug('Pop-up window built')

    def _build_name(self):
        name_font = tkfont.Font(
            size=FONT_SIZE+2,
            weight='bold',
            slant='roman'
        )
        tk.Label(
            self.main_frame, 
            text=self.name, 
            font=name_font,
            padx=3,
            pady=3
            ).pack(side='top')

    def _build_value(self):
        value_frame = tk.Frame(self.main_frame)
        value_frame.pack(pady=(10, 0), fill='x')
        
        tk.Label(value_frame, text='Value', font=self.font).pack(side='left')

        if self.type_raw == 'bool':
            self.build_bool_editor(value_frame)

        elif self.type_raw == 'choice':
            self.build_choice_editor(value_frame)

        elif self.type_raw == 'percent':
            self.build_percent_editor(value_frame)

        elif self.type_raw == 'hex_color':
            self.build_color_editor(value_frame)

        else:
            self.build_entry_editor(value_frame)

    def _build_source(self):
        source_frame = tk.Frame(self.main_frame)
        source_frame.pack(pady=(10, 0), fill='x')
        
        tk.Label(
            source_frame, 
            text='Source', 
            font=self.font,
            ).pack(side='left')
        
        tk.Label(
            source_frame, 
            text=self.source.capitalize(),
            font=self.font,
            relief='groove',
            bd=2
            ).pack(side='right', padx=(20, 10))

    def _build_type(self):
        type_frame = tk.Frame(self.main_frame)
        type_frame.pack(pady=(10, 0), fill='x')
        
        tk.Label(
            type_frame, 
            text='Type',
            font=self.font,
            ).pack(side='left')
        
        tk.Label(
            type_frame, 
            text=self.type_.capitalize(),
            font=self.font,
            wraplength=TYPE_WRAP_LEN,
            justify='left',
            relief='groove',
            bd=2,
            padx=3,
            pady=3
            ).pack(side='right', padx=(20, 10))

    def _build_desc(self):
        desc_font = tkfont.Font(
            size=FONT_SIZE,
            slant='italic'
        )
        desc_frame = tk.Frame(self.main_frame)
        desc_frame.pack(pady=(30, 0), fill='x')
        
        tk.Label(
            desc_frame, 
            text=f'\"{self.desc}\"',
            font=desc_font,
            wraplength=DESC_WRAP_LEN,
            justify='left',
            relief='groove',
            bd=3,
            padx=3,
            pady=3
            ).pack(padx=3, pady=3)

    def _build_buttons(self):
        button_frame = tk.Frame(self.main_frame)
        button_frame.pack(side='bottom', pady=(20, 0))
        
        confirm_button = tk.Button(
            button_frame, 
            text='Confirm',
            font=self.font,
            command=self._on_confirm,
            bg=CONFIRM_COLOR,
            activebackground=CONFIRM_COLOR
            )
        confirm_button.pack(side='right')
        self.balloon.bind_widget(confirm_button, 'Apply modify (Enter)')
        
        cancel_button = tk.Button(
            button_frame, 
            text='Cancel',
            font=self.font,
            command=lambda *_: self.destroy(),
            bg=CANCEL_COLOR,
            activebackground=CANCEL_COLOR
            )
        cancel_button.pack(side='right', padx=(0, 10))
        self.balloon.bind_widget(cancel_button, 'Abandon modify (Esc)')

        unset_button = tk.Button(
            button_frame, 
            text='Unset',
            font=self.font,
            command=self._unset,
            bg=UNSET_COLOR,
            activebackground=UNSET_COLOR
            )
        unset_button.pack(side='left', padx=(10, 30))
        self.balloon.bind_widget(unset_button, 'Unset option (Del)')

    def _on_confirm(self, *_, force=True):
        value = self.get_val()
        if value != str(self.value) or force:
            self.set_value(self.name, value)
        self.destroy()

    def _unset(self, *_):
        self.unset_option(self.name)
        self.destroy()
