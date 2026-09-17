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
                        self._toast(f'Open \"{song}\"')
                        self._send_dash_request('open', song=song)
                        
                elif key in KEY_MAP.reload:
                    self._toast('Reload')
                    self._send_dash_request('load_last')

                elif key in KEY_MAP.play_all:
                    self._toast('Play all')
                    self._send_dash_request('play-all')

                elif key in KEY_MAP.toggle:
                    self._toast('Play/Pause')
                    self._send_dash_request('toggle')
                elif key in KEY_MAP.stop:
                    self._toast('Stop')
                    self._send_dash_request('stop')

                elif key in KEY_MAP.seek:
                    pos = self._get_input('Enter time (HH:MM:SS): ')
                    if pos != '':
                        self._toast(f'Jump to {pos}')
                        self._send_dash_request('seek', time=pos)

                elif key in KEY_MAP.forward:
                    self._toast(f'+{CONFIG.dash_pos_step}s')
                    self._send_dash_request('seek', time=f'+{CONFIG.dash_pos_step}')
                elif key in KEY_MAP.backward:
                    self._send_dash_request('seek', time=f'-{CONFIG.dash_pos_step}')
                    self._toast(f'-{CONFIG.dash_pos_step}s')

                elif key in KEY_MAP.dice:
                    self._toast('Dice')
                    self._send_dash_request('dice')
                elif key in KEY_MAP.shuffle:
                    self._toast('Toggle shuffle')
                    self._send_dash_request('shuffle')
                elif key in KEY_MAP.loop:
                    self._toast('Toggle loop')
                    self._send_dash_request('loop')
                elif key in KEY_MAP.reverse:
                    self._toast('Toggle reverse')
                    self._send_dash_request('reverse')
                elif key in KEY_MAP.lyric:
                    self._toast('Toggle online lyric')
                    self._send_dash_request('lyric')

                elif key in KEY_MAP.offset_increase:
                    self._toast(f'Lyric offset +{OFFSET_OVERLAY_STEP}ms')
                    self._send_dash_request('set_offset_overlay', autoincrement=True, offset=OFFSET_OVERLAY_STEP)
                elif key in KEY_MAP.offset_decrease:
                    self._toast(f'Lyric offset -{OFFSET_OVERLAY_STEP}ms')
                    self._send_dash_request('set_offset_overlay', autoincrement=True, offset=-OFFSET_OVERLAY_STEP)
                elif key in KEY_MAP.reset_offset:
                    self._toast('Lyric offset reset')
                    self._send_dash_request('set_offset_overlay', autoincrement=False, offset=0)

                elif key in KEY_MAP.prev:
                    self._toast('Previous song')
                    self._send_dash_request('prev')
                elif key in KEY_MAP.next:
                    self._toast('Next song')
                    self._send_dash_request('next')

                elif key in KEY_MAP.vol_up:
                    self._toast(f'Volume +{CONFIG.dash_volume_step}%')
                    self._send_dash_request('volume', volume=f'+{CONFIG.dash_volume_step}')

                elif key in KEY_MAP.vol_down:
                    self._toast(f'Volume -{CONFIG.dash_volume_step}%')
                    self._send_dash_request('volume', volume=f'-{CONFIG.dash_volume_step}')

                elif key in KEY_MAP.mute:
                    self._toast('Toggle mute')
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
                    self._toast('Select current song')
                    self.select_current = True

                elif key in KEY_MAP.filter:
                    self.filter = self._get_input('Enter filter: ').strip()
                    if self.filter != '':
                        self._toast(f'Filter set: {self.filter}')

                elif key in KEY_MAP.switch_select:
                    if len(self.song_nums) > 0:
                        try:
                            num = self.song_nums[self.song_selected] + 1
                        except IndexError:
                            ...
                        else:
                            self._toast(f'Switch to the {num}nd song')
                            self._send_dash_request('switch', number=num)
                elif key in KEY_MAP.poster:
                    self._toast('Toggle poster')
                    self.poster = not self.poster
                    self.show_help = False

                elif key in KEY_MAP.help:
                    self._toast('Show help')
                    self.show_help = not self.show_help
                    self.poster = False

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
                    self._toast('Redraw dashboard')
                    self.redraw = True

                elif key in KEY_MAP.quit:
                    self._toast('Exit')
                    self.exit()

            except KeyboardInterrupt:
                self.exit()