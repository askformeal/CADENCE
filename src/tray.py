from threading import Thread
from time import sleep, time
from pathlib import Path
from tkinter import filedialog

from pystray import Icon, Menu, MenuItem
from PIL import Image

from src.log import setup_logger
from src.constants import ICON_PATH, ERROR_ICON_PATH, HEARTBEAT_POLL_INTERVAL, TRAY_POLL_INTERVAL, TRAY_ERROR_DISPLAY_TIME
from src.constants import AUDIO_FILE_TYPES
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
        self.ok_icon = Image.open(Path(ICON_PATH).open('rb'))
        self.error_icon = Image.open(Path(ERROR_ICON_PATH).open('rb'))

        super().__init__('cadence', self.ok_icon)
        self._last_sig = None
        self.error_time = 0
        self.is_error_icon = False
        logger.debug(f'{__name__} initiated')

    def _update(self):
        while self.running:
            try:
                title = 'CADENCE'
                
                songs_sub_menu = Menu(Label('---'))
                playlists_sub_menu = [MenuItem('[Play All]', lambda *_: self._send_tray_request('play-all'))]

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
                        self._shuffle = status.shuffle_raw
                    if status.loop_raw is not None:
                        self._loop = status.loop_raw 

                current_songs = self._send_tray_request('list', silent=True)
                if current_songs is not None:
                    if len(current_songs) == 0:
                        songs_sub_menu = Menu(Label('Empty'))
                    else:
                        song_buttons = []
                        for i, song in enumerate(current_songs):
                            name = SongOutput(song).display_name
                            if name is None:
                                name = 'N/A'
                            song_buttons.append(MenuItem(f'{i+1}. {name}', lambda *_, n=i+1: self._send_tray_request('switch', number=n)))
                        songs_sub_menu = Menu(*song_buttons)

                playlists = self._send_tray_request('lib.playlist.list', silent=True)
                if playlists is not None:
                    if len(playlists) > 0:
                        for playlist in playlists:
                            name = playlist['name']
                            playlists_sub_menu.append(MenuItem(name, lambda *_, x=name: self._send_tray_request('open', song=x)))

                playlists_sub_menu = Menu(*playlists_sub_menu)

                menu = Menu(
                    Label(title),
                    MenuItem('Open', self._open_file),
                    Menu.SEPARATOR,
                    MenuItem('Play/Pause', lambda *_: self._send_tray_request('toggle'), default=True),
                    MenuItem('Previous Song', lambda *_: self._send_tray_request('prev')),
                    MenuItem('Next Song', lambda *_: self._send_tray_request('next')),
                    MenuItem('Switch', songs_sub_menu),
                    MenuItem('Dice', lambda *_: self._send_tray_request('dice')),
                    MenuItem('Stop', lambda *_: self._send_tray_request('stop')),
                    MenuItem('Replay', lambda *_: self._send_tray_request('replay')),
                    MenuItem('Jump', Menu(
                        MenuItem('0%', lambda *_: self._send_tray_request('jump', progress=0)),
                        MenuItem('25%', lambda *_: self._send_tray_request('jump', progress=25)),
                        MenuItem('50%', lambda *_: self._send_tray_request('jump', progress=50)),
                        MenuItem('75%', lambda *_: self._send_tray_request('jump', progress=75)),
                        MenuItem('100%', lambda *_: self._send_tray_request('jump', progress=100)),
                    )),
                    Menu.SEPARATOR,
                    MenuItem('Playlists', playlists_sub_menu),
                    Menu.SEPARATOR,
                    MenuItem('Shuffle', lambda *_: self._send_tray_request('shuffle'), checked=lambda *_: self._shuffle),
                    MenuItem('Loop', lambda *_: self._send_tray_request('loop'), checked=lambda *_: self._loop),
                    Menu.SEPARATOR,
                    MenuItem('Mute', lambda *_: self._send_tray_request('mute'), checked=lambda *_: self._mute),
                    MenuItem('Volume', Menu(
                        MenuItem('0%', lambda *_: self._send_tray_request('volume', volume=0)),
                        MenuItem('25%', lambda *_: self._send_tray_request('volume', volume=25)),
                        MenuItem('50%', lambda *_: self._send_tray_request('volume', volume=50)),
                        MenuItem('75%', lambda *_: self._send_tray_request('volume', volume=75)),
                        MenuItem('100%', lambda *_: self._send_tray_request('volume', volume=100)),
                    )),
                    Menu.SEPARATOR,
                    MenuItem('Quit Tray', lambda *_: self.exit()),
                    MenuItem('Exit CADENCE', lambda *_: self._send_tray_request('exit')),
                )

                self.title = title
                sig = (str(menu), self._mute, self._shuffle, self._loop)
                if sig != self._last_sig:
                    self._last_sig = sig
                    self.menu = menu

                if (time() - self.error_time) < TRAY_ERROR_DISPLAY_TIME:
                    if not self.is_error_icon:
                        self.icon = self.error_icon
                        self.is_error_icon = True

                elif self.is_error_icon:
                    self.icon = self.ok_icon
                    self.is_error_icon = False
                
                sleep(TRAY_POLL_INTERVAL)
            except Exception as e:
                logger.exception('An error occurred during updating icon')

    def _open_file(self, *_):
        file_types = list(map(lambda x: (x[0], '*'+x[1]), AUDIO_FILE_TYPES))
        path = filedialog.askopenfilename(
            title= 'Select a song file',
            filetypes=file_types,
        )
        if path != '':
            self._send_tray_request('open', song=path)

    def _send_tray_request(self, action, silent=False, **kwargs):
        request = {'action': action, 'source': 'tray', 'notify_support': False, 'silent': silent}
        response = send_request(**request, **kwargs)
        if response.get('code', None) != 0:
            self.error_time = time()
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