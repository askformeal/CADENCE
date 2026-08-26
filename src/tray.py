from importlib.resources import files
from threading import Thread
from time import sleep

from pystray import Icon, Menu, MenuItem
from PIL import Image

from src.log import setup_logger
from src.constants import ICON_FILENAME, HEARTBEAT_POLL_INTERVAL, TRAY_POLL_INTERVAL
from src.constants import TRAY_LOG_PATH
from src.client import send_request, test_heartbeat, handle_code
from src.song_output import SongOutput

logger = setup_logger(__name__, TRAY_LOG_PATH)

class Label(MenuItem):
    def __init__(self, text):
        super().__init__(text, None, enabled=False)
class Tray(Icon):
    def __init__(self):
        self.running = True
        image = Image.open((files('res') / ICON_FILENAME).open('rb'))
        super().__init__('cadence', image)
        self._last_sig = None
        logger.debug(f'{__name__} initiated')

    def _update(self):
        while self.running:
            try:
                title = 'CADENCE'
                
                playlist_sub_menu = Menu(Label('---'))
                self._mute = None
                self._shuffle = None
                self._loop = None
            
                status = self._send_tray_request('status', silent=True)
                if status is not None:
                    status = SongOutput(status, prettify_none=False)
                    if status.display_name is not None:
                        title = f'Playing: {status.display_name}'
                    if status.player_status is not None:
                        title += f' ({status.player_status.capitalize()})'
                    if status.mute_raw is not None:
                        self._mute = status.mute_raw # fucking lying pystray only accepts nones and callbacks for checked for some reason
                    if status.shuffle_raw is not None:
                        self._shuffle = status.shuffle_raw # fucking lying pystray only accepts nones and callbacks for checked for some reason
                    if status.loop_raw is not None:
                        self._loop = status.loop_raw # fucking lying pystray only accepts nones and callbacks for checked for some reason

                playlist = self._send_tray_request('list', silent=True)
                if playlist is not None:
                    if len(playlist) == 0:
                        playlist_sub_menu = Menu(Label('Empty'))
                    else:
                        song_buttons = []
                        for i, song in enumerate(playlist):
                            name = SongOutput(song).display_name
                            if name is None:
                                name = 'N/A'
                            song_buttons.append(MenuItem(f'{i+1}. {name}', lambda *_, n=i+1: self._send_tray_request('switch', number=n)))
                        playlist_sub_menu = Menu(*song_buttons)                    
                        

                menu = Menu(
                    MenuItem('Play/Pause', lambda *_: self._send_tray_request('toggle'), default=True),
                    MenuItem('Previous Song', lambda *_: self._send_tray_request('prev')),
                    MenuItem('Next Song', lambda *_: self._send_tray_request('next')),
                    MenuItem('Switch', playlist_sub_menu),
                    MenuItem('Stop', lambda *_: self._send_tray_request('stop')),
                    Menu.SEPARATOR,
                    MenuItem('Mute', lambda *_: self._send_tray_request('mute'), checked=lambda *_: self._mute),
                    MenuItem('Shuffle', lambda *_: self._send_tray_request('shuffle'), checked=lambda *_: self._shuffle),
                    MenuItem('Loop', lambda *_: self._send_tray_request('loop'), checked=lambda *_: self._loop),
                    Menu.SEPARATOR,
                    MenuItem('Quit Tray', lambda *_: self.exit()),
                    MenuItem('Exit CADENCE', lambda *_: self._send_tray_request('exit')),
                )

                self.title = title
                sig = (str(menu), self._mute, self._shuffle, self._loop)
                if sig != self._last_sig:
                    self._last_sig = sig
                    self.menu = menu
                
                sleep(TRAY_POLL_INTERVAL)
            except Exception as e:
                logger.exception('An error occurred during updating icon')

    def _send_tray_request(self, action, silent=False, **kwargs):
        request = {'action': action, 'source': 'tray', 'notify_support': False, 'silent': silent}
        response = send_request(**request, **kwargs)
        if not silent:
            logger.info(f'Sent request: {request}, response received: {response}')
        handle_code(response.get('code', None), self.exit)
        return response.get('attachment', None)

    def start(self):
        Thread(target=self.run, daemon=True).start()
        Thread(target=self._update, daemon=True).start()
        logger.info('Tray icon running')
        try:
            while self.running:
                sleep(HEARTBEAT_POLL_INTERVAL)
                code = test_heartbeat()
                handle_code(code, self.exit)

        except KeyboardInterrupt:
            ...

    def exit(self):
        self.stop()
        self.running = False

if __name__ == '__main__':
    Tray().start()