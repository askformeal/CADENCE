import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont

from PIL import Image, ImageTk

from .logger import logger
from src.utils.tui import strlen
from src.constants.paths import (
    ICON_PATH, 
    REMOTE_ICON_PATH,
    REFRESH_ICON_PATH
    )
from src.constants.config_gui import (
    INIT_REMOTE,
    TITLE,
    RESIZE,
    ICON_SIZE,
    FONT_SIZE
)
from src.config_manager import CONFIG_MANAGER
from src.frontend.client import send_request
from .pop_up import Popup

class ConfigGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        self.title(TITLE)
        self.iconbitmap(ICON_PATH)
        self.resizable(*RESIZE)

        self.bind('<F5>', self._update_options)
        self.bind('<r>', self._toggle_remote)

        self.remote = INIT_REMOTE
        self.options = []
        self.option_good = False

        self._build_window()
        logger.debug(f'{__name__} initialized')

    def _build_window(self):
        button_frame = tk.Frame(self)
        button_frame.pack(side='top', fill='x')

        self.remote_image = self._get_icon(REMOTE_ICON_PATH)
        self.refresh_image = self._get_icon(REFRESH_ICON_PATH)

        self.remote_button = tk.Button(
            button_frame,
            command=self._toggle_remote,
            relief='sunken',
            image=self.remote_image
            )

        self.refresh_button = tk.Button(
            button_frame,
            command=self._update_options,
            image=self.refresh_image
            )

        self.remote_button.pack(side='right', padx=(0, 20))
        self.refresh_button.pack(side='right', padx=(0, 20))

        main_frame = tk.Frame(self)
        main_frame.pack(padx=10, pady=5, fill='x', expand=True)

        font = tkfont.Font(size=FONT_SIZE)
        self.option_list = tk.Listbox(main_frame, font=font)
        self.option_list.pack(side='left', fill='x', expand=True)
        self.option_list.bind('<Return>', self._on_select)
        self.option_list.bind('<KP_Enter>', self._on_select)
        self.option_list.bind('<Double-Button-1>', self._on_select)

        scroll_bar = tk.Scrollbar(main_frame)
        scroll_bar.pack(side='left', fill='y')

        self.option_list.config(yscrollcommand=scroll_bar.set)
        scroll_bar.config(command=self.option_list.yview)

        self._update_options()

    def _get_icon(self, path):
        image = Image.open(path)
        image = image.resize(ICON_SIZE, Image.Resampling.LANCZOS)
        image = ImageTk.PhotoImage(image)
        return image

    def _toggle_remote(self, *_):
        self.remote = not self.remote
        if self.remote:
            self.remote_button.config(relief='sunken')
        else:
            self.remote_button.config(relief='raised')
        logger.info(f'Remote mode set: {self.remote}')
        self._update_options()

    def _on_select(self, *_):
        if self.option_good:
            selected = self.option_list.curselection()
            if len(selected) > 0:
                option = self.options[selected[0]]
                logger.info(f'Option open: {option}')
                Popup(self, option)
            else:
                logger.info(f'No option selected')

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

        lines = []
        for option in info:
            name = option['name']
            value = option['value']
            source = option['source']
            if value == '':
                value = '<empty>'

            lines.append(f'{name}:  {value}       [{source.upper()}]')
            
        self.options = info

        if len(lines) == 0:
            lines = ['No options available']
            self.option_good = False
        else:
            self.option_good = True
            
        max_len = max(map(strlen, lines))

        old_yview = self.option_list.yview()[0]
        selected = self.option_list.curselection()
        if len(selected) > 0:
            old_index = selected[0]
        else:
            old_index = 0

        self.option_list.delete(0, tk.END)
        self.option_list.config(width=max_len)
        for line in lines:
            self.option_list.insert(tk.END, line)

        self.option_list.yview_moveto(old_yview)
        self.option_list.select_set(old_index)

        logger.info(f'Updated option(s)')

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
