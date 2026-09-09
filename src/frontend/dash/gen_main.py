from wcwidth import wcswidth

from src import __version__
from src.constants import MAX_SHOW_LYRIC, MIN_WIDTH, VOL_BAR_LEN
from src.sentinels import SENTINELS
from src.utils.lyric import get_lyric_line
from src.utils.time_ import format_time
from src.utils.tui import align, center, progress_bar, window_list, wrap_text


def gen_main_text(snapshot, toast, box):
    lyric_lines = ['No Lyric']
    if isinstance(snapshot.time, int):
        if snapshot.lyric is SENTINELS.LYRIC_LOADING:
            lyric_lines = ['[Loading ...]']
        else:
            current_line = get_lyric_line(snapshot.lyric, snapshot.time, snapshot.lyric_offset + snapshot.offset_overlay)
            if current_line is not SENTINELS.EMPTY_LYRIC:
                text = list(map(lambda x:x[1], snapshot.lyric))
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
    if snapshot.lyric_offset != 0 or snapshot.offset_overlay != 0:
        lines += [f'Offset: {snapshot.lyric_offset}']
        if snapshot.offset_overlay != 0:
            if snapshot.offset_overlay > 0:
                offset_overlay_display = f'+{snapshot.offset_overlay}'
            else:
                offset_overlay_display = str(snapshot.offset_overlay)
            lines[-1] += f' ({offset_overlay_display})'

    lines += [
        '{lyric}',
        '{toast}'
        ]

    max_len = max(max(map(wcswidth, lines)), MIN_WIDTH)

    title = center(f'CADENCE {__version__} Dashboard', max_len)
    separator = '='*max_len
    current = snapshot.current_num
    if isinstance(current, int):
        current += 1

    song_info = center(f'{snapshot.display_name} [{current}/{snapshot.playlist_len}]', max_len)

    if not isinstance(snapshot.time, int) or not isinstance(snapshot.length, int) or snapshot.time <= 0 or snapshot.length <= 0:
        bar = progress_bar(0, max_len-20)
        pos_num = '--:--:--/--:--:--'
    else:
        progress = snapshot.time / snapshot.length
        pos_num = f'{format_time(snapshot.time)}/{format_time(snapshot.length)}'
        bar = progress_bar((max_len-20) * progress, max_len-20)
    
    pos = center(f'{bar} [{pos_num}]', max_len)
    
    lyric = box(center('\n'.join(lyric_lines), max_len-4))

    if not isinstance(snapshot.volume, int):
        bar = progress_bar(0, VOL_BAR_LEN)
        vol_num = '?%'
    else:
        bar = progress_bar(VOL_BAR_LEN*snapshot.volume/100, VOL_BAR_LEN)
        vol_num = f'{snapshot.volume}%'
    if snapshot.mute:
        vol_num += ' [MUTE]'
    volume = f'{bar} [{vol_num}]'
    
    state = align(max_len, volume, f"{snapshot.online_lyric}{snapshot.shuffle}{snapshot.loop}{snapshot.player_status}")

    toast = wrap_text(toast, max_len)
    
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