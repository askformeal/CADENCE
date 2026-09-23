import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageTk

from .logger import logger
from src.constants.paths import (
    ICON_PATH, 
    REMOTE_ICON_PATH,
    REFRESH_ICON_PATH,
    EDIT_ICON_PATH,
    OPEN_FILE_ICON_PATH,
    COPY_PATH_ICON_PATH
    )
from src.constants.config_gui import (
    TITLE,
    WIDTH, HEIGHT,
    POS_X, POS_Y,

    EDIT_COLOR,
    NO_OPTION_COLOR,
    VALUE_COLOR,
    DEFAULT_VALUE_COLOR,
    CONFIG_FILE_COLOR,
    INVALID_SOURCE_COLOR,
    REMOTE_ON_COLOR,
    REMOTE_OFF_COLOR,
    REFRESH_COLOR,
    OPEN_COLOR,
    COPY_COLOR,
    RESIZE,
    ICON_SIZE,
    FONT_SIZE,

    BALLOON_BG, 
    BALLOON_WRAP,
    BALLOON_OFFSET_X,
    BALLOON_OFFSET_Y,
    BALLOON_WINDUP,
)
from src.config import CONFIG
from src.config_manager import CONFIG_MANAGER
from src.frontend.client import send_request
from src.frontend.tkinter_widget.scrolled_frame import ScrolledFrame
from src.frontend.tkinter_widget.balloon import Balloon
from .pop_up import Popup
from .handler import HandlerMixin

class ConfigGUI(tk.Tk, HandlerMixin):
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

        self.remote = CONFIG.config_default_remote
        self.options = {}

        self.balloon = Balloon(
            self,
            bg=BALLOON_BG,
            wrap_len=BALLOON_WRAP,
            offset_x=BALLOON_OFFSET_X,
            offset_y=BALLOON_OFFSET_Y,
            windup=BALLOON_WINDUP
            )

        self._build_window()
        logger.debug(f'{__name__} initialized')

    def _build_window(self):
        button_frame = tk.Frame(self)
        button_frame.pack(side='top', fill='x')

        self.remote_image = self._get_icon(REMOTE_ICON_PATH)
        self.refresh_image = self._get_icon(REFRESH_ICON_PATH)
        self.edit_image = self._get_icon(EDIT_ICON_PATH)
        self.open_image = self._get_icon(OPEN_FILE_ICON_PATH)
        self.copy_image = self._get_icon(COPY_PATH_ICON_PATH)

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

        self.open_button = tk.Button(
            button_frame,
            command=self.open_file,
            image=self.open_image,
            bg=OPEN_COLOR,
            activebackground=OPEN_COLOR
            )
        self.copy_button = tk.Button(
            button_frame,
            command=self.copy_path,
            image=self.copy_image,
            bg=COPY_COLOR,
            activebackground=COPY_COLOR
            )

        self._update_remote_button()

        self.remote_button.pack(side='right', padx=(0, 20))
        self.refresh_button.pack(side='right', padx=(0, 20))
        self.open_button.pack(side='left', padx=(20, 0))
        self.copy_button.pack(side='left', padx=(20, 0))

        self.balloon.bind_widget(self.remote_button, 'Toggle remote mode')
        self.balloon.bind_widget(self.refresh_button, 'Refresh')
        self.balloon.bind_widget(self.open_button, 'Open configure file')
        self.balloon.bind_widget(self.copy_button, 'Copy configure file path')

        main_frame = tk.Frame(self)
        main_frame.pack(padx=10, pady=10, fill='both', expand=True)

        self.option_frame = ScrolledFrame(
            main_frame, 
            relief='groove', 
            bd=3,
            padx=5,
            pady=5,
            )
        self.option_frame.pack(fill='both', expand=True)

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

        self._handle_response(response, update=False)

        logger.debug(f'Fetched info of {len(info)} option(s) from {route}')

        no_option_font = tkfont.Font(
            size=FONT_SIZE + 2,
            weight='bold'
        )

        self.options = {}
        old_yview = self.option_frame.yview()[0]
        self.option_frame.clear()
        if len(info) == 0:
            self.option_frame.lock_scroll = True
            tk.Label(
                self.option_frame.frame,
                text='No options available',
                font=no_option_font,
                fg=NO_OPTION_COLOR
                ).pack(pady=(20,0))
        else:
            self.option_frame.lock_scroll = False
            for option in info:
                self._build_option(option).pack(fill='x', pady=5)

                name = option['name']
                self.options[name] = option

        self.option_frame.yview_moveto(old_yview)

        logger.info(f'Updated option(s)')

    def _build_option(self, option):
        font = tkfont.Font(
            size=FONT_SIZE
        )
        empty_font = tkfont.Font(
            size=FONT_SIZE,
            slant='italic'
        )

        name = option['name']
        value = option['value']
        source = option['source']
        type_ = option['type']
        desc = option['description']

        frame = tk.Frame(
            self.option_frame.frame, 
            relief='solid',
            bd = 3,
            padx=10,
            pady=10,
            )
        
        name_label = tk.Label(
            frame,
            text=name,
            font=font,
            padx=3,
            pady=3
            )
        name_label.pack(side='left')
        self.balloon.bind_widget(name_label, desc)
        
        value_label = tk.Label(frame, padx=5, pady=3)
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
        self.balloon.bind_widget(value_label, f'Type: {type_}')
        
        
        edit_button = tk.Button(
            frame,
            image=self.edit_image,
            bg=EDIT_COLOR,
            command=lambda x=name: self._on_edit(x)
            )
        
        edit_button.pack(side='right', padx=(20,10))
        self.balloon.bind_widget(edit_button, f'Edit \"{name}\"')
        
        
        if source == 'default value':
            source_bg = DEFAULT_VALUE_COLOR
        elif source == 'configure file':
            source_bg = CONFIG_FILE_COLOR
        else:
            source_bg = INVALID_SOURCE_COLOR
        
        source_label = tk.Label(
            frame,
            text=source.capitalize(),
            font=font,
            relief='sunken',
            bg=source_bg,
            padx=3,
            pady=3
            )
        source_label.pack(side='right', padx=(20,0))

        return frame        

    def _on_edit(self, name):
        info = self.options[name]
        Popup(self, info)

    def _send_config_request(self, action, **kwargs):
        request = {'action': action, 'source': 'config_gui', 'notify_support': False, **kwargs}
        response = send_request(**request)
        logger.info(f'Sent request: {request}')
        return response

    def run(self):
        self.deiconify()
        logger.info('Start main loop')
        try:
            self.mainloop()
        except KeyboardInterrupt:
            ...

if __name__ == '__main__':
    ConfigGUI().run()
