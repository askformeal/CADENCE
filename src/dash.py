import time
import os
import logging
import math
from threading import Thread

from wcwidth import wcswidth
import readchar

from src import version
from src.log import setup_logger
from src.constants import DASH_LOG_PATH
from src.constants import HEARTBEAT_POLL_INTERVAL, DASH_POLL_INTERVAL
from src.constants import DASH_MAX_SHOW_SONG
from src.constants import DASH_KEY_MAP as KEY_MAP
from src.client import test_heartbeat, handle_code, send_request
from src.song_output import SongOutput
from src.utils import box, center

logger = setup_logger(__name__, DASH_LOG_PATH)
for handler in logger.handlers:
    if isinstance(handler, logging.StreamHandler):
        handler.setLevel(logging.WARNING)

class Dash:
    def __init__(self):
        os.system('')
        self.running = True

        self.selected = 0 # 0-based!

        self.old_text = ''

        print('\033[?1049h', end='')
        print('\033[?25l', end='')
        logger.debug(f'{__name__} initiated')

    def _listen_hotkey(self):
        while self.running:
            try:
                key = readchar.readkey()
                logger.debug(f'Read key: {key}')
                if key in KEY_MAP.quit:
                    self.exit()
                elif key in KEY_MAP.toggle:
                    self._send_dash_request('toggle')

                elif key in KEY_MAP.prev:
                    self._send_dash_request('prev')
                elif key in KEY_MAP.next:
                    self._send_dash_request('next')

                elif key in KEY_MAP.select_up:
                    self.selected -= 1
                elif key in KEY_MAP.select_down:
                    self.selected += 1
                elif key in KEY_MAP.select_current:
                    if isinstance(self.current_num, int):
                        self.selected = self.current_num - 1
                elif key in KEY_MAP.switch_select:
                    self._send_dash_request('switch', number=self.selected+1)
            except KeyboardInterrupt:
                self.exit()

    def _update(self):
        while self.running:
            try:
                self.display_name = '-'
                self.artist = '-'
                self.album = '-'
                self.current_num = '-' # 1-based!
                self.playlist_len = '-'
                self.player_status = '-'
                songs_lines = ['---']

                status = self._send_dash_request('status', silent=True)
                if status is not None:
                    status = SongOutput(status)
                    self.display_name = status.display_name
                    self.artist = status.artist
                    self.album = status.album
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
                                songs_lines.append(song_info)
                                if i == self.selected:
                                    songs_lines[-1] = f'[{songs_lines[-1]}]'
                                if i+1 == self.current_num:
                                    songs_lines[-1] = f'> {songs_lines[-1]} <'

                        for i, line in enumerate(songs_lines):
                            pad = ' ' * (max_len - wcswidth(line))
                            songs_lines[i] = line + pad

                songs_lines = box('\n'.join(songs_lines)).split('\n')



                lines = ['{title}']
                lines += [
                    '\n{separator}\n',
                    '{song_info}\n',
                    '{album}\n'
                    ]
                lines += songs_lines
                lines += ['\n{player_status}']

                max_len = max(map(wcswidth, lines))

                title = center(f'CADENCE {version} Dashboard', max_len)
                separator = '='*max_len
                song_info = center(f'{self.display_name} - {self.artist} [{self.current_num}/{self.playlist_len}]', max_len)
                album = center(f'Album: {self.album}', max_len)
                player_status = f'[{self.player_status}]'
                player_status = f'{' '*(max_len-wcswidth(player_status))}{player_status}'

                text = '\n'.join(lines)
                text = text.format(
                    title=title, 
                    separator=separator, 
                    song_info=song_info,
                    album=album,
                    player_status=player_status
                    )
                text = box(text, l_pad=2, r_pad=2)


                if text != self.old_text:
                    if self.old_text != '':
                        print(f'\033[{len(self.old_text.split('\n'))}F\033[J', end='')
                    print(text)
                    self.old_text = text
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