import time
import os
from threading import Thread

from wcwidth import wcswidth
import readchar

from src import version
from src.log import setup_logger
from src.constants import DASH_LOG_PATH, DASH_MAX_SHOW_BIND, DASH_MAX_SHOW_LYRIC, DASH_MIN_WIDTH
from src.constants import HEARTBEAT_POLL_INTERVAL, DASH_POLL_INTERVAL
from src.constants import DASH_MAX_SHOW_SONG, DASH_POS_BAR_LEN, DASH_VOL_BAR_LEN, DASH_TOAST_TIME
from src.constants import DASH_KEY_MAP as KEY_MAP
from src.constants import BOX_STYLES
from src.config import CONFIG
from src.client import test_heartbeat, handle_code, send_request

from src.sentinels import SENTINELS
from src.song_output import SongOutput
from src.utils import box, center, get_lyric_line, progress_bar, align, format_time, window_list, squeeze, wrap_text

logger = setup_logger(__name__, DASH_LOG_PATH, add_console=False)

class Dash:
    def __init__(self):
        os.system('')
        self.running = True

        self.song_selected = 0 # 0-based!
        self.bind_selected = 0 # 0-based!

        self.filter = ''

        self.paused = False

        self.old_text = ''
        self.redraw = True
        self.box_styles = list(BOX_STYLES.keys())
        self.box_style_num = self.box_styles.index(CONFIG.dash_box_style)

        self.show_help = False

        self.toast_text = ''
        self.toast_time = 0

        self.lyric = {}

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
                        self.song_selected -= DASH_MAX_SHOW_SONG
                elif key in KEY_MAP.page_down:
                    if self.show_help:
                        self.bind_selected += DASH_MAX_SHOW_BIND
                    else:
                        self.song_selected += DASH_MAX_SHOW_SONG

                elif key in KEY_MAP.select_current:
                    if isinstance(self.current_num, int):
                        try:
                            self.song_selected = self.songs_nums.index(self.current_num)
                        except ValueError:
                            ...

                elif key in KEY_MAP.filter:
                    self.filter = self._get_input('Enter filter: ').strip()

                elif key in KEY_MAP.switch_select:
                    if len(self.songs_nums) > 0:
                        num = self.songs_nums[self.song_selected] + 1
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
                        
                    self.bind_selected = squeeze(self.bind_selected, len(bind_lines)-1)
                    
                    bind_lines = window_list(bind_lines, DASH_MAX_SHOW_BIND, self.bind_selected)
                    bind_lines = self._dash_box('\n'.join(bind_lines)).split('\n')
                    lines += bind_lines
                    text = '\n'.join(lines)
                    
                else:
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
                    lyric_lines = ['[MISSING]']
                    self.songs_nums = [] # to prevent selected_song -> actual number in playlist mismatch when filter is applied

                    status = self._send_dash_request('status', silent=True)
                    if status is not None:
                        status = SongOutput(status, prettify_none=False)
                        self.display_name = status.display_name
                        self.artist = status.artist
                        self.album = status.album
                        lyric_path = status.lyric_raw
                        self.time = status.time_raw
                        self.length = status.length_raw
                        self.volume = status.volume
                        self.mute = status.mute_raw
                        self.shuffle = {True: '[Shuffle] ', False: '', None: '?'}[status.shuffle_raw]
                        self.loop = {True: '[Loop] ', False: '', None: '?'}[status.loop_raw]
                        self.current_num = status.current_num
                        if isinstance(self.current_num, int):
                            self.current_num -= 1
                        self.playlist_len = status.playlist_len
                        self.player_status = status.player_status
                        if self.player_status is None:
                            self.player_status = 'N/A'
                        else:
                            self.player_status = f'[{self.player_status.capitalize()}]'

                        if self.lyric.get('path', None) != lyric_path:
                            self.lyric = self._send_dash_request('lyric')
                            if self.lyric is None:
                                self.lyric = {'path': lyric_path}
                            if self.lyric != {}:
                                logger.debug(f'Lyric file update: {self.lyric}')

                    lyric_lines = ['No Lyric']
                    if isinstance(self.time, int):
                        current_line = get_lyric_line(self.lyric.get('lyric', []), self.time)
                        if current_line is not None:
                            text = list(map(lambda x:x[1], self.lyric.get('lyric', [])))
                            if current_line is SENTINELS.BEFORE_FIRST_LYRIC:
                                current_line = 0
                                text = ['...'] + text
                            lyric_lines = window_list(text, DASH_MAX_SHOW_LYRIC, current_line, newline_selected=True, mark_unshown=False, left_align=False)
                    
                    songs = self._send_dash_request('list', silent=True)
                    if songs is not None:
                        if len(songs) == 0:
                            songs_lines = ['Player Empty']
                        else:
                            songs_lines = []
                            self.songs_nums = []
                            for i, song in enumerate(songs):
                                song = SongOutput(song)
                                filter = self.filter.lower()
                                if filter in song.display_name.lower() or filter in song.artist.lower():
                                    song_info = f'{song.display_name} - {song.artist}'
                                    songs_lines.append((song_info))
                                    self.songs_nums.append(i)

                            if len(songs_lines) == 0:
                                songs_lines = ['No matches of filter']
                            else:
                                self.song_selected = squeeze(self.song_selected, len(songs_lines)-1)
                                current = None
                                if isinstance(self.current_num, int):
                                    try:
                                        current = self.songs_nums.index(self.current_num)
                                    except ValueError:
                                        ...

                                songs_lines = window_list(songs_lines, DASH_MAX_SHOW_SONG, self.song_selected, current=current, filter=self.filter)
                                if self.filter != '':
                                    songs_lines = [f'Filter: \"{self.filter}\"', *songs_lines]

                                songs_lines = ['Playlist\n', *songs_lines]

                    # songs_lines = self._dash_box('\n'.join(songs_lines)).split('\n')

                    lines = ['{title}']
                    lines += [
                        '\n{separator}\n',
                        '{song_info}\n',
                        '{album}\n',
                        '{pos}\n',
                        '{lyric}\n',
                        '{state}\n\n',
                        ]
                    lines += [
                        '{toast}'
                        ]

                    max_len = max(max(map(wcswidth, lines)), DASH_MIN_WIDTH)

                    title = center(f'CADENCE {version} Dashboard', max_len)
                    separator = '='*max_len
                    current = self.current_num
                    if isinstance(current, int):
                        current += 1

                    song_info = center(f'{self.display_name} - {self.artist} [{current}/{self.playlist_len}]', max_len)

                    if not isinstance(self.time, int) or not isinstance(self.length, int) or self.time <= 0 or self.length <= 0:
                        bar = progress_bar(0, DASH_POS_BAR_LEN)
                        pos_num = '--:--:--/--:--:--'
                    else:
                        progress = self.time / self.length
                        bar = progress_bar(DASH_POS_BAR_LEN * progress, DASH_POS_BAR_LEN)
                        pos_num = f'{format_time(self.time)}/{format_time(self.length)}'

                    pos = center(f'{bar} [{pos_num}]', max_len)

                    album = center(f'Album: {self.album}', max_len)

                    lyric = self._dash_box(center('\n'.join(lyric_lines), max_len-4))

                    if not isinstance(self.volume, int):
                        bar = progress_bar(0, DASH_VOL_BAR_LEN)
                        vol_num = '?%'
                    else:
                        bar = progress_bar(DASH_VOL_BAR_LEN*self.volume/100, DASH_VOL_BAR_LEN)
                        vol_num = f'{self.volume}%'
                    if self.mute:
                        vol_num += ' [MUTE]'
                    volume = f'{bar} [{vol_num}]'

                    state = align(max_len, volume, f"{self.shuffle}{self.loop}{self.player_status}")

                    playlist = '\n'.join(songs_lines)

                    if (time.time() - self.toast_time) <= DASH_TOAST_TIME:
                        toast = wrap_text(self.toast_text, max_len)
                    else:
                        toast = ''

                    text = '\n'.join(lines)
                    text = text.format(
                        title=title, 
                        separator=separator, 
                        song_info=song_info,
                        album=album,
                        pos=pos,
                        lyric=lyric,
                        state=state,
                        toast=toast
                        )
                text = self._dash_box(text, playlist, l_pad=2, r_pad=2)


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

    def _send_dash_request(self, action, silent=False, **kwargs):
        request = {'action': action, 'source': 'dash', 'notify_support': False, 'silent': silent, **kwargs}
        response = send_request(**request)
        if response.get('code', None) != 0:
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
        print('\033[?1049l')
        logger.info('Exit dashboard frontend')
        self.running = False
            
if __name__ == '__main__':
    Dash().run()