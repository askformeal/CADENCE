import time
import os
import math
from threading import Thread

from wcwidth import wcswidth
import readchar

from src import version
from src.log import setup_logger
from src.constants import DASH_LOG_PATH
from src.constants import HEARTBEAT_POLL_INTERVAL, DASH_POLL_INTERVAL
from src.constants import DASH_MAX_SHOW_SONG, DASH_VOL_BAR_LEN, DASH_TOAST_TIME
from src.constants import DASH_KEY_MAP as KEY_MAP
from src.constants import BOX_STYLES
from src.config import CONFIG
from src.client import test_heartbeat, handle_code, send_request
from src.song_output import SongOutput
from src.utils import box, center, progress_bar, align

logger = setup_logger(__name__, DASH_LOG_PATH, add_console=False)

class Dash:
    def __init__(self):
        os.system('')
        self.running = True

        self.selected = 0 # 0-based!

        self.old_text = ''
        self.redraw = False
        self.box_styles = list(BOX_STYLES.keys())
        self.box_style_num = self.box_styles.index(CONFIG.dash_box_style)

        self.toast_text = ''
        self.toast_time = 0

        print('\033[?1049h', end='')
        print('\033[?25l', end='')
        logger.debug(f'{__name__} initiated')

    def _listen_hotkey(self):
        while self.running:
            try:
                key = readchar.readkey()
                logger.debug(f'Read key: {key}')

                if key in KEY_MAP.toggle:
                    self._send_dash_request('toggle')
                elif key in KEY_MAP.stop:
                    self._send_dash_request('stop')
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
                    if isinstance(self.volume, int):
                        self.volume += CONFIG.dash_volume_step
                        self.volume = min(self.volume, 100)
                        self._send_dash_request('volume', volume=self.volume)
                elif key in KEY_MAP.vol_down:
                    if isinstance(self.volume, int):
                        self.volume -= CONFIG.dash_volume_step
                        self.volume = max(self.volume, 0)
                        self._send_dash_request('volume', volume=self.volume)
                elif key in KEY_MAP.mute:
                    self._send_dash_request('mute')
                    

                elif key in KEY_MAP.select_up:
                    self.selected -= 1
                elif key in KEY_MAP.select_down:
                    self.selected += 1
                elif key in KEY_MAP.page_up:
                    self.selected -= DASH_MAX_SHOW_SONG
                elif key in KEY_MAP.page_down:
                    self.selected += DASH_MAX_SHOW_SONG
                elif key in KEY_MAP.select_current:
                    if isinstance(self.current_num, int):
                        self.selected = self.current_num - 1
                elif key in KEY_MAP.switch_select:
                    self._send_dash_request('switch', number=self.selected+1)

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
                self.display_name = '[MISSING]'
                self.artist = '[MISSING]'
                self.album = '[MISSING]'
                self.time = '[MISSING]'
                self.length = '[MISSING]'
                self.volume = '[MISSING]'
                self.mute = '[MISSING]'
                self.shuffle = '[MISSING]'
                self.loop = '[MISSING]'
                self.current_num = '[MISSING]' # 1-based!
                self.playlist_len = '[MISSING]'
                self.player_status = '[MISSING]'
                songs_lines = ['[MISSING]']

                status = self._send_dash_request('status', silent=True)
                if status is not None:
                    status = SongOutput(status)
                    self.display_name = status.display_name
                    self.artist = status.artist
                    self.album = status.album
                    self.time = status.time
                    self.length = status.length
                    self.volume = status.volume
                    self.mute = status.mute_raw
                    self.shuffle = {True: '[Shuffle]', False: '', None: '?'}[status.shuffle_raw]
                    self.loop = {True: '[Loop]', False: '', None: '?'}[status.loop_raw]
                    self.current_num = status.current_num
                    self.playlist_len = status.playlist_len
                    self.player_status = status.player_status.capitalize()

                songs = self._send_dash_request('list', silent=True)
                if songs is not None:
                    if len(songs) == 0:
                        songs_lines = ['---']
                    else:
                        songs_lines = []

                        if self.selected >= len(songs):
                            self.selected = len(songs) - 1
                        elif self.selected < 0:
                            self.selected = 0

                        above_selector_num = math.ceil(self.selected - DASH_MAX_SHOW_SONG / 2)
                        below_selector_num = math.ceil(self.selected + DASH_MAX_SHOW_SONG / 2)

                        if above_selector_num < 0:
                            below_selector_num -= above_selector_num
                            above_selector_num = 0

                        if below_selector_num >= len(songs):
                            above_selector_num -= below_selector_num - len(songs) + 1
                            below_selector_num = len(songs) - 1

                        max_len = 0

                        for i, song in enumerate(songs):
                            song = SongOutput(song)
                            song_info = f'{i+1}. {song.display_name} - {song.artist}'
                            max_len = max(max_len, wcswidth(song_info))                            


                            if i in range(above_selector_num, below_selector_num+1):    
                                if i == self.selected:
                                    song_info = f'[{song_info}]'
                                if i+1 == self.current_num:
                                    song_info = f'> {song_info} <'
                                songs_lines.append(song_info)


                        for i, line in enumerate(songs_lines):
                            pad = ' ' * (max_len + 6 - wcswidth(line)) # why 6? because len('> [] <') == 6
                            songs_lines[i] = line + pad

                songs_lines = self._dash_box('\n'.join(songs_lines)).split('\n')



                lines = ['{title}']
                lines += [
                    '\n{separator}\n',
                    '{song_info}\n',
                    '{album}\n',
                    '{state}',
                    '{player_status}',
                    ]
                lines += songs_lines
                lines += ['{toast}']

                max_len = max(map(wcswidth, lines))

                title = center(f'CADENCE {version} Dashboard', max_len)
                separator = '='*max_len
                song_info = center(f'{self.display_name} - {self.artist} [{self.current_num}/{self.playlist_len}]', max_len)
                album = center(f'Album: {self.album}', max_len)

                if not isinstance(self.volume, int):
                    bar = progress_bar(0, DASH_VOL_BAR_LEN)
                    vol_num = '?%'
                else:
                    bar = progress_bar(DASH_VOL_BAR_LEN*self.volume/100, DASH_VOL_BAR_LEN)
                    vol_num = f'{self.volume}%'
                if self.mute:
                    vol_num += ' [MUTE]'
                volume = f'[{bar}] {vol_num}'

                state = align(max_len, volume, f'{self.shuffle} {self.loop}')

                player_status = align(max_len, right=f'[{self.player_status}]')

                if (time.time() - self.toast_time) <= DASH_TOAST_TIME:
                    toast = self.toast_text
                else:
                    toast = ''

                text = '\n'.join(lines)
                text = text.format(
                    title=title, 
                    separator=separator, 
                    song_info=song_info,
                    album=album,
                    state=state,
                    player_status=player_status,
                    toast=toast
                    )
                text = self._dash_box(text, l_pad=2, r_pad=2)


                if text != self.old_text or self.redraw:
                    if self.old_text != '':
                        print(f'\033[{len(self.old_text.split('\n'))}F\033[J', end='')
                    print(text)
                    self.old_text = text
                    self.redraw = False
                time.sleep(DASH_POLL_INTERVAL)

            except Exception as e:
                logger.exception('An error occurred during updating dashboard')
                self.exit()

    def _send_dash_request(self, action, silent=False, **kwargs):
        request = {'action': action, 'source': 'dash', 'notify_support': False, 'silent': silent, **kwargs}
        response = send_request(**request)
        if not silent:
            logger.info(f'Sent request: {request}, response received: {response}')
        handle_code(response.get('code', None), self.exit)
        return response.get('attachment', None)

    def _toast(self, text):
        self.toast_text = text
        self.toast_time = time.time()

    def _dash_box(self, *args, **kwargs):
        return box(*args, style=self.box_styles[self.box_style_num], **kwargs)

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
        print('\033[?25h', end='')
        print('\033[?1049l')
        logger.info('Exit dashboard frontend')
        self.running = False
            
if __name__ == '__main__':
    Dash().run()