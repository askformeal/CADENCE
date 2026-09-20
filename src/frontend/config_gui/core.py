import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont

from PIL import Image, ImageTk

from .logger import logger
from src.constants.paths import (
    ICON_PATH, 
    REMOTE_ICON_PATH,
    REFRESH_ICON_PATH,
    EDIT_ICON_PATH
    )
from src.constants.config_gui import (
    INIT_REMOTE,
    TITLE,
    WIDTH, HEIGHT,
    POS_X, POS_Y,
    EDIT_COLOR,
    VALUE_COLOR,
    DEFAULT_VALUE_COLOR,
    CONFIG_FILE_COLOR,
    INVALID_SOURCE_COLOR,
    REMOTE_ON_COLOR,
    REMOTE_OFF_COLOR,
    REFRESH_COLOR,
    RESIZE,
    ICON_SIZE,
    FONT_SIZE
)
from src.config_manager import CONFIG_MANAGER
from src.frontend.client import send_request
from .scrolled_frame import ScrolledFrame
from .pop_up import Popup

class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        self.title(TITLE)
        self.iconbitmap(ICON_PATH)
        self.geometry(f'{WIDTH}x{HEIGHT}+{POS_X}+{POS_Y}')
        self.resizable(*RESIZE)

        self.bind('<Escape>', lambda *_: self.destroy())
        self.bind('<F5>', self._update_options)
        self.bind('<r>', self._toggle_remote)

        self.remote = INIT_REMOTE
        self.options = {}

        self._build_window()
        logger.debug(f'{__name__} initialized')

    def _build_window(self):
        button_frame = tk.Frame(self)
        button_frame.pack(side='top', fill='x')

        self.remote_image = self._get_icon(REMOTE_ICON_PATH)
        self.refresh_image = self._get_icon(REFRESH_ICON_PATH)
        self.edit_image = self._get_icon(EDIT_ICON_PATH)

        self.remote_button = tk.Button(
            button_frame,
            command=self._toggle_remote,
            image=self.remote_image
            )

        self.refresh_button = tk.Button(
            button_frame,
            command=self._update_options,
            image=self.refresh_image,
            bg=REFRESH_COLOR,
            activebackground=REFRESH_COLOR
            )
        self._update_remote_button()

        self.remote_button.pack(side='right', padx=(0, 20))
        self.refresh_button.pack(side='right', padx=(0, 20))

        main_frame = tk.Frame(self)
        main_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.option_scroll = ScrolledFrame(
            main_frame, 
            relief='groove', 
            bd=3,
            padx=5,
            pady=5
            )
        self.option_scroll.pack(fill='both', expand=True)

        self._update_options()

    def _get_icon(self, path):
        image = Image.open(path)
        image = image.resize(ICON_SIZE, Image.Resampling.LANCZOS)
        image = ImageTk.PhotoImage(image)
        return image

    def _toggle_remote(self, *_):
        self.remote = not self.remote
        self._update_remote_button()
        self._update_options()

    def _update_remote_button(self):
        if self.remote:
            self.remote_button.config(
                relief='sunken', 
                bg=REMOTE_ON_COLOR, 
                activebackground=REMOTE_ON_COLOR
                )
        else:
            self.remote_button.config(
                relief='raised', 
                bg=REMOTE_OFF_COLOR,
                activebackground=REMOTE_OFF_COLOR
                )
            
        logger.info(f'Remote mode set: {self.remote}')

    def _update_options(self, *_):
        if self.remote:
            route = 'remote'
            response = self._send_config_request('config.list')
            info = response['attachment']
            if info == {}:
                info = []
        else:
            route = 'local'
            response = CONFIG_MANAGER.get_all_option_info()
            info = response.attachment

        logger.debug(f'Fetched info of {len(info)} option(s) from {route}')

        font = tkfont.Font(
            size=FONT_SIZE
        )
        empty_font = tkfont.Font(
            size=FONT_SIZE,
            slant='italic'
        )

        self.options = {}
        old_yview = self.option_scroll.yview()[0]
        self.option_scroll.clear()
        for option in info:
            name = option['name']
            value = option['value']
            source = option['source']

            self.options[name] = option

            option_frame = tk.Frame(
                self.option_scroll.frame, 
                relief='solid',
                bd = 3,
                padx=10,
                pady=10,
                )

            name_label = tk.Label(
                option_frame,
                text=name,
                font=font,
                padx=3,
                pady=3
                )
            name_label.pack(side='left')

            value_label = tk.Label(option_frame, padx=5, pady=3)
            value_label.pack(side='left', padx=(20,0))
            if value == '':
                value_label.config(
                    text='<Empty>', 
                    font=empty_font,
                    fg='grey',
                    )
            else:
                value_label.config(
                    text=str(value),
                    font=font,
                    relief='groove',
                    bd=2,
                    bg=VALUE_COLOR,
                )

                
            edit_button = tk.Button(
                option_frame,
                image=self.edit_image,
                bg=EDIT_COLOR,
                command=lambda x=name: self._on_edit(x)
                )

            edit_button.pack(side='right', padx=(20,10))

            option_frame.pack(fill='x', pady=5)

            if source == 'default value':
                source_bg = DEFAULT_VALUE_COLOR
            elif source == 'configure file':
                source_bg = CONFIG_FILE_COLOR
            else:
                source_bg = INVALID_SOURCE_COLOR

            source_label = tk.Label(
                option_frame,
                text=source.capitalize(),
                font=font,
                relief='sunken',
                bg=source_bg,
                padx=3,
                pady=3
                )
            source_label.pack(side='right', padx=(20,0))

        self.option_scroll.yview_moveto(old_yview)

        logger.info(f'Updated option(s)')

    def _on_edit(self, name):
        info = self.options[name]
        Popup(self, info)

    def set_value(self, name, value, overwrite_corrupt=False):
        logger.info(f'Set \"{name}\" to \"{value}\", overwrite corrupted: {overwrite_corrupt}')
        if self.remote:
            response = self._send_config_request(
                'config.set', 
                option=name, 
                value=value,
                overwrite_corrupt=overwrite_corrupt
                )
        else:
            response = dict(CONFIG_MANAGER.set_option_value(
                name=name,
                value=value,
                overwrite_corrupt=overwrite_corrupt
            ))

        self._handle_response(response)

    def unset(self, name):
        logger.info(f'Unset: {name}')
        if self.remote:
            response = self._send_config_request('config.unset', option=name)
        else:
            response = CONFIG_MANAGER.unset_option(name)
        self._handle_response(response)

    def _handle_response(self, response):
        if response['code'] == 0:
            self._update_options()
        else:
            msg = response['msg']
            messagebox.showerror(
                'Failed', 
                message='Unsuccessful response',
                detail=msg
                )

    def _send_config_request(self, action, **kwargs):
        request = {'action': action, 'source': 'config_gui', 'notify_support': False, **kwargs}
        response = send_request(**request)
        logger.info(f'Sent request: {request}, response received: {response}')
        return response

    def run(self):
        self.deiconify()
        logger.info('Start main loop')
        self.mainloop()

if __name__ == '__main__':
    ConfigGUI().run()
