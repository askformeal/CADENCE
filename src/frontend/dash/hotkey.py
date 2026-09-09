from .logger import logger

import readchar

from src.constants import DASH_KEY_MAP as KEY_MAP
from src.constants import MAX_SHOW_BIND, OFFSET_OVERLAY_STEP
from src.config import CONFIG

class HotkeyMixin:
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
                elif key in KEY_MAP.lyric:
                    self._send_dash_request('lyric')

                elif key in KEY_MAP.offset_increase:
                    self._send_dash_request('set_offset_overlay', autoincrement=True, offset=OFFSET_OVERLAY_STEP)
                elif key in KEY_MAP.offset_decrease:
                    self._send_dash_request('set_offset_overlay', autoincrement=True, offset=-OFFSET_OVERLAY_STEP)
                elif key in KEY_MAP.reset_offset:
                    self._send_dash_request('set_offset_overlay', autoincrement=False, offset=0)

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
                        self.bind_selected -= MAX_SHOW_BIND
                    else:
                        self.song_selected -= self.playlist_height
                elif key in KEY_MAP.page_down:
                    if self.show_help:
                        self.bind_selected += MAX_SHOW_BIND
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