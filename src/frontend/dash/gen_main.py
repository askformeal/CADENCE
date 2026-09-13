import time

from src import __version__
from src.constants import MAX_SHOW_LYRIC, MIN_WIDTH, VOL_BAR_LEN, TOAST_TIME
from src.sentinels import SENTINELS
from src.utils.lyric import get_lyric_line
from src.utils.escape_code import ESCAPE_CODE as EC
from src.utils.time_ import format_time
from src.utils.tui import (
    strlen, 
    align, 
    center, 
    progress_bar, 
    window_list, 
    wrap_text
    )
from .empty import DASH_EMPTY as EMPTY

class MainMixin:
    def gen_main_text(self):
        lyric_lines = ['No Lyric']

        if self.snapshot.lyric_loading is not EMPTY and self.snapshot.lyric_loading:
            lyric_lines = ['[Loading ...]']
            
        elif EMPTY not in (self.snapshot.time, 
                            self.snapshot.lyric,
                            self.snapshot.lyric_offset, 
                            self.snapshot.offset_overlay
                            ):
            current_line = get_lyric_line(self.snapshot.lyric, 
                                            self.snapshot.time, 
                                            self.snapshot.lyric_offset + self.snapshot.offset_overlay)
            
            if current_line is not SENTINELS.EMPTY_LYRIC:
                text = list(map(lambda x:x[1], self.snapshot.lyric))
                if current_line is SENTINELS.BEFORE_FIRST_LYRIC:
                    current_line = 0
                    text = ['...'] + text
                lyric_lines = window_list(text, MAX_SHOW_LYRIC, current_line, newline_selected=True, mark_unshown=False, left_align=False)

        lines = [
            '{title}'
            '\n{separator}\n',
            '{song_info}\n',
            '{pos}\n\n',
            '{state}\n',
            ]
        
        if (
            EMPTY not in (self.snapshot.lyric_offset,self.snapshot.offset_overlay) 
            and (self.snapshot.lyric_offset != 0 or self.snapshot.offset_overlay != 0)
            ):

            lines += [f'Offset: {self.snapshot.lyric_offset}']
            if self.snapshot.offset_overlay != 0:
                if self.snapshot.offset_overlay > 0:
                    offset_overlay_display = f'+{self.snapshot.offset_overlay}'
                else:
                    offset_overlay_display = str(self.snapshot.offset_overlay)
                lines[-1] += f' ({offset_overlay_display})'

        lines += [
            '{lyric}',
            '{toast}'
            ]

        max_len = max(max(map(strlen, lines)), MIN_WIDTH)

        title = center(f'{EC.bold}{EC.cyan}CADENCE {__version__} Dashboard{EC.rs}', max_len)
        separator = '='*max_len
        current = self.snapshot.current_num
        if current is not EMPTY:
            current += 1

        song_info = center(f'{self.snapshot.display_name} [{current}/{self.snapshot.playlist_len}]', max_len)

        if EMPTY in (self.snapshot.time, self.snapshot.length) or self.snapshot.time <= 0 or self.snapshot.length <= 0:
            bar = progress_bar(0, max_len-20)
            pos_num = '--:--:--/--:--:--'
        else:
            progress = self.snapshot.time / self.snapshot.length
            pos_num = f'{format_time(self.snapshot.time)}/{format_time(self.snapshot.length)}'
            bar = progress_bar((max_len-20) * progress, max_len-20)
        
        pos = center(f'{bar} [{pos_num}]', max_len)
        
        lyric = self._dash_box(center('\n'.join(lyric_lines), max_len-4))

        if self.snapshot.volume is EMPTY:
            bar = progress_bar(0, VOL_BAR_LEN)
            vol_num = '?%'
        else:
            bar = progress_bar(VOL_BAR_LEN*self.snapshot.volume/100, VOL_BAR_LEN)
            vol_num = f'{self.snapshot.volume}%'

        if self.snapshot.mute and self.snapshot.mute is not EMPTY:
            vol_num += ' [MUTE]'
        volume = f'{bar} [{vol_num}]'

        online_lyric = {True: '[Ol Lyric] ', False: '', EMPTY: '?'}[self.snapshot.online_lyric]
        shuffle = {True: '[Shuffle] ', False: '', EMPTY: '?'}[self.snapshot.shuffle]
        loop = {True: '[Loop] ', False: '', EMPTY: '?'}[self.snapshot.loop]
        if self.snapshot.player_status is EMPTY:
            player_status = 'N/A'
        else:
            player_status = f'[{self.snapshot.player_status.capitalize()}]'
        state = align(max_len, volume, f"{online_lyric}{shuffle}{loop}{player_status}")

        if (time.time() - self.toast_time) <= TOAST_TIME:
            toast = wrap_text(self.toast_text, max_len)
        else:
            toast = ''
        
        text = '\n'.join(lines)
        text = text.format(
            title=title, 
            separator=separator, 
            song_info=song_info,
            pos=pos,
            lyric=lyric,
            state=state,
            toast=toast
            )

        return text