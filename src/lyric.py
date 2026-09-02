# this the the floating lyric board frontend, not a module for all lyric-related features
from threading import Thread
import time
import tkinter as tk

from pystray import Icon, Menu, MenuItem
from PIL import Image

from src.client import handle_code, send_request, test_heartbeat
from src.constants import HEARTBEAT_POLL_INTERVAL, LYRIC_LOG_PATH, LYRIC_POLL_INTERVAL, LYRIC_ICON_PATH
from src.constants import LYRIC_TRANS_COLOR as TRANS_COLOR
from src.log import setup_logger
from src.sentinels import SENTINELS
from src.song_output import SongOutput
from src.utils import get_lyric_line

logger = setup_logger(__name__, LYRIC_LOG_PATH)

class Lyric(tk.Tk):
    def __init__(self):
        super().__init__()

        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.wm_attributes("-transparentcolor", TRANS_COLOR)
        self.config(bg=TRANS_COLOR)

        self.lyric = {}
        self.visibility = True
        self.lyric_on = True

        self.lyric_label = tk.Label(self,
                                    text='',
                                    fg='white',
                                    background=TRANS_COLOR)
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

                    if self.lyric.get('path', None) != lyric_path:
                        self.lyric = self._send_dash_request('lyric')
                        if self.lyric is None:
                            self.lyric = {'path': lyric_path}
                        if self.lyric != {}:
                            logger.debug(f"Lyric file update: {self.lyric['path']}")

                if self.lyric_on:
                    if pos is not None and self.lyric.get('lyric', None) is not None:
                        index = get_lyric_line(self.lyric['lyric'], pos)
                        if index is SENTINELS.BEFORE_FIRST_LYRIC:
                            current_line = '...'
                        elif index is SENTINELS.EMPTY_LYRIC:
                            current_line = '[Lyric Empty]'
                        else:
                            current_line = self.lyric['lyric'][index][1]
                        self.after(0, self.lyric_label.config, text=current_line)
                        self._show()
                    else:
                        self._hide()


                else:
                    self._hide()

                time.sleep(LYRIC_POLL_INTERVAL)

            except Exception as e:
                logger.exception('An error occurred during updating lyric board')
                self.exit()

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