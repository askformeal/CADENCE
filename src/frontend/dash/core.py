import shutil
import time
import os

from threading import Thread

import readchar

from src import __version__

from .logger import logger
from src.constants import DASH_MAX_SHOW_BIND
from src.constants import HEARTBEAT_POLL_INTERVAL, DASH_POLL_INTERVAL
from src.constants import DASH_KEY_MAP as KEY_MAP
from src.constants import DASH_MAX_SHOW_SONG, DASH_TOAST_TIME
from src.constants import BOX_STYLES
from src.config import CONFIG
from src.frontend.client import test_heartbeat, handle_code, send_request
from src.utils.misc import squeeze
from src.utils.tui import box, window_list
from .snapshot import Snapshot
from .gen_main import gen_main_text
from .gen_playlist import gen_playlist_text
from .gen_info import gen_info_text

class Dash:
    def __init__(self):
        os.system('')
        self.running = True

        self.snapshot = Snapshot(self._send_dash_request)

        self.song_selected = 0 # 0-based!
        self.bind_selected = 0 # 0-based!
        self.select_end = False
        self.select_current = False

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

    def _listen_hotkey(self):
        while self.running:
            try:
                key = readchar.readkey()
                logger.debug(f'Read key: {key}')

                if key in KEY_MAP.open:
                    song = self._get_input('Enter song name/library ID/file path/playlist name: ')
                    if song != '':
                        self._send_dash_request('open', song=song)

                elif key in KEY_MAP.play_all:
                    self._send_dash_request('play-all')

                elif key in KEY_MAP.toggle:
                    self._send_dash_request('toggle')
                elif key in KEY_MAP.stop:
                    self._send_dash_request('stop')

                elif key in KEY_MAP.seek:
                    pos = self._get_input('Enter time (HH:MM:SS): ')
                    if pos != '':
                        self._send_dash_request('seek', time=pos)

                elif key in KEY_MAP.forward:
                    self._send_dash_request('seek', time=f'+{CONFIG.dash_pos_step}')
                elif key in KEY_MAP.backward:
                    self._send_dash_request('seek', time=f'-{CONFIG.dash_pos_step}')

                elif key in KEY_MAP.dice:
                    self._send_dash_request('dice')
                elif key in KEY_MAP.shuffle:
                    self._send_dash_request('shuffle')
                elif key in KEY_MAP.loop:
                    self._send_dash_request('loop')

                elif key in KEY_MAP.prev:
                    self._send_dash_request('prev')
                elif key in KEY_MAP.next:
                    self._send_dash_request('next')

                elif key in KEY_MAP.vol_up:
                    self._send_dash_request('volume', volume=f'+{CONFIG.dash_volume_step}')

                elif key in KEY_MAP.vol_down:
                    self._send_dash_request('volume', volume=f'-{CONFIG.dash_volume_step}')

                elif key in KEY_MAP.mute:
                    self._send_dash_request('mute')
                    

                elif key in KEY_MAP.select_up:
                    if self.show_help:
                        self.bind_selected -= 1
                    else:
                        self.song_selected -= 1
                elif key in KEY_MAP.select_down:
                    if self.show_help:
                        self.bind_selected += 1
                    else:
                        self.song_selected += 1

                elif key in KEY_MAP.page_up:
                    if self.show_help:
                        self.bind_selected -= DASH_MAX_SHOW_BIND
                    else:
                        self.song_selected -= self.playlist_height
                elif key in KEY_MAP.page_down:
                    if self.show_help:
                        self.bind_selected += DASH_MAX_SHOW_BIND
                    else:
                        self.song_selected += self.playlist_height

                elif key in KEY_MAP.home:
                    if self.show_help:
                        self.bind_selected = 0
                    else:
                        self.song_selected = 0

                elif key in KEY_MAP.end:
                    self.select_end = True
                    
                elif key in KEY_MAP.select_current:
                    self.select_current = True

                elif key in KEY_MAP.filter:
                    self.snapshot.filter = self._get_input('Enter filter: ').strip()

                elif key in KEY_MAP.switch_select:
                    if len(self.snapshot.songs_nums) > 0:
                        num = self.snapshot.songs_nums[self.song_selected] + 1
                        self._send_dash_request('switch', number=num)

                elif key in KEY_MAP.help:
                    self.show_help = not self.show_help

                elif key in KEY_MAP.prev_box:
                    self.box_style_num -= 1
                    if self.box_style_num < 0:
                        self.box_style_num = len(self.box_styles) - 1
                    self._toast(f'Theme: {self.box_styles[self.box_style_num]}')
                    self.redraw = True                    

                elif key in KEY_MAP.next_box:
                    self.box_style_num += 1
                    if self.box_style_num >= len(self.box_styles):
                        self.box_style_num = 0
                    self._toast(f'Theme: {self.box_styles[self.box_style_num]}')
                    self.redraw = True                    

                elif key in KEY_MAP.redraw:
                    self.redraw = True

                elif key in KEY_MAP.quit:
                    self.exit()

            except KeyboardInterrupt:
                self.exit()

    def _update(self):
        while self.running:
            try:
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
                    
                    bind_lines = window_list(bind_lines, DASH_MAX_SHOW_BIND, self.bind_selected)
                    bind_lines = self._dash_box('\n'.join(bind_lines)).split('\n')
                    lines += bind_lines
                    text = '\n'.join(lines)
                    
                else:
                    self.snapshot.poll()

                    if self.select_end:
                        self.song_selected = len(self.snapshot.current_songs) - 1
                        self.select_end = False

                    elif self.select_current:
                        try:
                            self.song_selected = self.snapshot.songs_nums.index(self.snapshot.current_num)
                        except ValueError:
                            self.song_selected = 0
                        self.select_current = False
                    else:                                
                        self.song_selected = squeeze(self.song_selected, len(self.snapshot.current_songs)-1)

                    if (time.time() - self.toast_time) <= DASH_TOAST_TIME:
                        toast = self.toast_text
                    else:
                        toast = ''

                    if CONFIG.auto_dash_height:
                        self.playlist_height = max(shutil.get_terminal_size((0, DASH_MAX_SHOW_SONG+12)).lines-12, 1)
                    else:
                        self.playlist_height = DASH_MAX_SHOW_SONG

                    main_text = gen_main_text(self.snapshot, toast, self._dash_box)
                    # logger.debug(f'x: {self.song_selected}')/
                    playlist_text = gen_playlist_text(self.snapshot, self.playlist_height, self.song_selected)
                    info_text = gen_info_text(self.snapshot)

                text = self._dash_box(info_text, main_text, playlist_text, l_pad=2, r_pad=2)

                if (text != self.old_text or self.redraw) and not self.paused:
                    if self.old_text != '':
                        print(f'\033[2J\033[H', end='')
                    print(text)
                    self.old_text = text
                    self.redraw = False
                time.sleep(DASH_POLL_INTERVAL)

            except Exception as e:
                logger.exception('An error occurred during updating dashboard')
                self.exit()

    def _send_dash_request(self, action, silent=False, expect_fail=False, **kwargs):
        request = {'action': action, 'source': 'dash', 'notify_support': False, 'silent': silent, **kwargs}
        response = send_request(**request)
        if response.get('code', None) != 0 and not expect_fail:
            self._toast(f"[Failed] {response.get('msg', 'No message')}")
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