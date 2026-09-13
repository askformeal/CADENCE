from pathlib import Path
import re
import shutil
import time
import os

from threading import Thread

from src import __version__

from .logger import logger
from src.constants import MAX_SHOW_BIND
from src.constants import HEARTBEAT_POLL_INTERVAL, POLL_INTERVAL
from src.constants import DASH_KEY_MAP as KEY_MAP
from src.constants import MAX_SHOW_SONG, BOX_STYLES
from src.config import CONFIG
from src.frontend.client import test_heartbeat, handle_code, send_request
from src.utils.escape_code import ESCAPE_CODE as EC
from src.utils.misc import squeeze, get_song_display_name
from src.utils.tui import strlen, box, window_list
from src.frontend.snapshot import Snapshot
from .empty import DASH_EMPTY as EMPTY
from .hotkey import HotkeyMixin
from .gen_main import MainMixin
from .gen_playlist import PlaylistMixin
from .gen_info import InfoMixin

class Dash(HotkeyMixin, MainMixin, PlaylistMixin, InfoMixin):
    def __init__(self):
        os.system('')
        self.running = True

        self.snapshot = Snapshot(
            self._send_dash_request, 
            empty=EMPTY)

        self.song_selected = 0 # 0-based!
        self.bind_selected = 0 # 0-based!
        self.filtered_songs = []
        self.song_nums = []
        self.select_end = False
        self.select_current = False

        self.filter = ''

        self.playlist_height = 0

        self.paused = False

        self.old_text = ''
        self.redraw = True
        self.box_styles = list(BOX_STYLES.keys())
        self.box_style_num = self.box_styles.index(CONFIG.dash_box_style)

        self.show_help = False

        self.toast_text = ''
        self.toast_time = 0

        self.use_buffer = CONFIG.dash_screen_buffer

        if self.use_buffer:
            print('\033[?1049h', end='')
        self._cursor_off()
        logger.debug(f'{__name__} initiated')

    def _get_input(self, msg=''):
        self.paused = True
        self._cursor_on()
        result = input(msg)
        self._cursor_off()
        self.paused = False
        self.redraw = True

        return result

    def _update(self):
        while self.running:
            try:
                main_text = ''
                playlist_text = ''
                info_text = ''

                if self.show_help:
                    lines = ['Key Map\n']
                    bind_lines = []
                    for bind in vars(KEY_MAP).values():
                        keys = ', '.join(list(map(lambda x: f'[{x}]', bind.key_names)))
                        bind_lines.append(f'{bind.name}: {keys}')

                    if self.select_end:
                        self.bind_selected = len(bind_lines) - 1
                        self.select_end = False
                    else:
                        self.bind_selected = squeeze(self.bind_selected, len(bind_lines)-1)
                    
                    bind_lines = window_list(bind_lines, MAX_SHOW_BIND, self.bind_selected)
                    bind_lines = self._dash_box('\n'.join(bind_lines)).split('\n')
                    lines += bind_lines
                    text = '\n'.join(lines)
                    
                else:
                    self.snapshot.poll()

                    self.filtered_songs = []
                    self.song_nums = []
                    if self.snapshot.current_songs is not EMPTY:
                        for i, song in enumerate(self.snapshot.current_songs):
                            name = song.get('name', None)
                            if name is None:
                                name = ''
                            else:
                                name = name.lower()
                        
                            path_stem = song.get('path', None)
                            if path_stem is None:
                                path_stem = ''
                            else:
                                path_stem = Path(path_stem).stem.lower()
                        
                            artist = song.get('artist')
                            if artist is None:
                                artist = ''
                            else:
                                artist = artist.lower()
                            filter_ = self.filter.lower()
                            if filter_ in name or filter_ in path_stem or filter_ in artist:
                                display_name = get_song_display_name(song)
                                if display_name is None:
                                    display_name = 'N/A'

                                self.filtered_songs.append(display_name)
                                self.song_nums.append(i)

                    if self.select_end:
                        self.song_selected = max(len(self.filtered_songs) - 1, 0)
                        self.select_end = False

                    elif self.select_current:
                        if self.snapshot.current_num is EMPTY:
                            self.song_selected = 0
                        else:
                            try:
                                self.song_selected = self.song_nums.index(self.snapshot.current_num)
                            except ValueError:
                                self.song_selected = 0
                        self.select_current = False
                    else:                                
                        self.song_selected = squeeze(self.song_selected, max(len(self.filtered_songs)-1, 0))

                    if CONFIG.auto_dash_height:
                        self.playlist_height = max(shutil.get_terminal_size((0, MAX_SHOW_SONG+12)).lines-12, 1)
                    else:
                        self.playlist_height = MAX_SHOW_SONG

                    main_text = self.gen_main_text()
                    playlist_text = self.gen_playlist_text()
                    info_text = self.gen_info_text()

                    text = self._dash_box(info_text, main_text, playlist_text, l_pad=2, r_pad=2)

                width = shutil.get_terminal_size((-1, -1)).columns
                text_lines = text.splitlines()
                text = ''
                for line in text_lines:
                    if width != -1:
                        while strlen(line) > width:
                            last_escape = re.findall(r'\x1b\[[0-?]*[ -/]*[@-~]$', line)
                            if len(last_escape) > 0:
                                last_escape = last_escape[0]
                                line = line[:-len(last_escape)]
                            else:
                                line = line[:-1]

                    text += f'{line}{EC.rs}\n'

                if (text != self.old_text or self.redraw) and not self.paused:
                    if self.old_text != '':
                        print(f'\033[2J\033[H', end='')
                    print(text)

                    self.old_text = text
                    self.redraw = False
                time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.exception('An error occurred during updating dashboard')
                self.exit()

    def _send_dash_request(self, action, silent=False, expect_fail=False, **kwargs):
        request = {'action': action, 'source': 'dash', 'notify_support': False, 'silent': silent, **kwargs}
        response = send_request(**request)
        if response.get('code', None) != 0 and not expect_fail:
            self._toast(f"{EC.red}{EC.bold}[Failed]{EC.rs} {response.get('msg', 'No message')}")
        if not silent:
            logger.info(f'Sent request: {request}, response received: {response}')
        handle_code(response.get('code', None), self.exit)
        return response.get('attachment', None)

    def _toast(self, text):
        self.toast_text = text
        self.toast_time = time.time()

    def _dash_box(self, *args, **kwargs):
        return box(*args, style=self.box_styles[self.box_style_num], **kwargs)

    def _cursor_on(self):
        print('\033[?25h', end='')

    def _cursor_off(self):
        print('\033[?25l', end='')

    def run(self):
        logger.info('Dashboard started')
        Thread(target=self._update, daemon=True).start()
        Thread(target=self._listen_hotkey, daemon=True).start()
        try:
            while self.running:
                time.sleep(HEARTBEAT_POLL_INTERVAL)
                code = test_heartbeat()
                handle_code(code, self.exit)
        except KeyboardInterrupt:
            ...

    def exit(self):
        self._cursor_on()
        if self.use_buffer:
            print('\033[?1049l')
        logger.info('Exit dashboard frontend')
        self.running = False
            
if __name__ == '__main__':
    Dash().run()