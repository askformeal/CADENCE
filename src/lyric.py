# this the the floating lyric board frontend, not a module for all lyric-related features
from threading import Thread
import time
import tkinter as tk
from tkinter import font as tkfont

from pystray import Icon, Menu, MenuItem
from PIL import Image

from src.client import handle_code, send_request, test_heartbeat
from src.config import CONFIG
from src.constants import HEARTBEAT_POLL_INTERVAL, LYRIC_LOG_PATH, LYRIC_POLL_INTERVAL, LYRIC_ICON_PATH
from src.constants import LYRIC_HOVER_EXTENSION as HOVER_EXT
from src.log import setup_logger
from src.sentinels import SENTINELS
from src.song_output import SongOutput
from src.utils import get_lyric_line, squeeze
from src.utils import hex_color_to_dec as dec_hex

logger = setup_logger(__name__, LYRIC_LOG_PATH)

class Lyric(tk.Tk):
    def __init__(self):
        super().__init__()

        i = 0
        while i in (dec_hex(CONFIG.lyric_font_color), dec_hex(CONFIG.lyric_bg_color)):
            i += 1
        
        self.trans_color = f"#{format(i, '06X')}"

        self.overrideredirect(True)
        self.attributes('-topmost', True)

        self.attributes('-alpha', CONFIG.lyric_opacity / 100)
        self.config(bg=self.trans_color)

        self.wm_attributes("-transparentcolor", self.trans_color)

        self.hover = False
        self.after(100, self._check_hover)

        self.lyric = {}
        self.visibility = True
        self.lyric_on = True

        family = CONFIG.lyric_font_family
        if family == '':
            family = tkfont.nametofont('TkDefaultFont').actual('family')

        font_size = CONFIG.lyric_font_size

        if CONFIG.lyric_font_bold:
            font_weight = 'bold'
        else:
            font_weight = 'normal'

        self.lyric_label = tk.Label(self,
                                    text='',
                                    padx=15,
                                    pady=7,
                                    foreground=CONFIG.lyric_font_color,
                                    background=self.trans_color,
                                    font=tkfont.Font(
                                        family=family, 
                                        size=font_size, 
                                        weight=font_weight,
                                        )
                                    )
        self.lyric_label.pack()

        menu = (
            MenuItem('Show/Hide', lambda *_: self._toggle(), default=True),
            Menu.SEPARATOR,
            MenuItem('Quit', lambda *_: self.exit())
        )

        self.icon = Icon(
            'cadence_lyric', 
            Image.open(LYRIC_ICON_PATH),
            'CADENCE Lyric Board',
            menu=menu
            )

        logger.debug(f'{__name__} initiated')

    def _check_hover(self):
        self.update_idletasks()
        win_x_left, win_y_up = self.winfo_x(), self.winfo_y()
        win_x_right = win_x_left + self.winfo_width()
        win_y_down = win_y_up + self.winfo_height()

        pointer_x, pointer_y = self.winfo_pointerxy()
        if pointer_x in range(win_x_left-HOVER_EXT, win_x_right+1+HOVER_EXT) and pointer_y in range(win_y_up-HOVER_EXT, win_y_down+1+HOVER_EXT):
            if not self.hover:
                self.attributes('-alpha', 1)
                self.lyric_label.config(bg=CONFIG.lyric_bg_color)
                self.hover = True
        else:
            if self.hover:
                self.attributes('-alpha', CONFIG.lyric_opacity / 100)
                self.lyric_label.config(bg=self.trans_color)
                self.hover = False

        self.after(100, self._check_hover)

    def _toggle(self, *_):
        self.lyric_on = not self.lyric_on

    def _show(self):
        if not self.visibility:
            self.after(0, self.deiconify)
            self.visibility = True

    def _hide(self):
        if self.visibility:
            self.after(0, self.withdraw)
            self.visibility = False

    def _update_lyric(self):
        while True:
            try:
                lyric_path = None
                pos = None

                status = self._send_dash_request('status', silent=True)
                if status is not None:
                    status = SongOutput(status, prettify_none=False)
                    lyric_path = status.lyric_raw
                    pos = status.time_raw
                    state = status.player_status

                    if self.lyric.get('path', None) != lyric_path:
                        self.lyric = self._send_dash_request('lyric')
                        if self.lyric is None:
                            self.lyric = {'path': lyric_path}
                        if self.lyric != {}:
                            logger.debug(f"Lyric file update: {self.lyric['path']}")

                if self.lyric_on and (state == 'playing' or (state == 'paused' and not CONFIG.pause_hide_lyric)):
                    if pos is not None and self.lyric.get('lyric', None) is not None:
                        index = get_lyric_line(self.lyric['lyric'], pos)
                        if index is SENTINELS.BEFORE_FIRST_LYRIC:
                            current_line = '...'
                        elif index is SENTINELS.EMPTY_LYRIC:
                            current_line = '[Lyric Empty]'
                        else:
                            current_line = self.lyric['lyric'][index][1]
                        
                        self.after(0, self._update_text, text=current_line)

                        self._show()
                    else:
                        self._hide()


                else:
                    self._hide()

                time.sleep(LYRIC_POLL_INTERVAL)

            except Exception as e:
                logger.exception('An error occurred during updating lyric board')
                self.exit()

    def _update_text(self, text):
        self.lyric_label.config(text=text)
        self.update_idletasks()
        x_pos = (self.winfo_screenwidth() - self.winfo_width()) // 2 + CONFIG.lyric_x_offset
        x_pos = squeeze(x_pos, self.winfo_screenwidth())
        y_pos = min(CONFIG.lyric_height, self.winfo_screenheight())
        self.geometry(f'+{x_pos}-{y_pos}')
        
    def _send_dash_request(self, action, silent=False, **kwargs):
        request = {'action': action, 'source': 'lyric', 'notify_support': False, 'silent': silent, **kwargs}
        response = send_request(**request)
        if not silent:
            logger.info(f'Sent request: {request}, response received: {response}')
        handle_code(response.get('code', None), self.exit)
        return response.get('attachment', None)

    def _check_heartbeat(self):
        while True:
            time.sleep(HEARTBEAT_POLL_INTERVAL)
            code = test_heartbeat()
            handle_code(code, self.exit)

    def exit(self):
        self.destroy()
        self.icon.stop()

    def run(self):
        Thread(target=self._check_heartbeat, daemon=True).start()
        Thread(target=self._update_lyric, daemon=True).start()
        Thread(target=self.icon.run, daemon=True).start()
        try:
            self.mainloop()
        except KeyboardInterrupt:
            ...

if __name__ == '__main__':
    Lyric().run()