import os

import pytest

from src.utils import verify_path_format, box, center


@pytest.mark.parametrize('raw,expected', [
    ('', False),
    ('   ', False),
    ('a\x00b.flac', False),
])
def test_verify_path_format_generic(raw, expected):
    assert verify_path_format(raw) is expected


@pytest.mark.parametrize('raw,expected', [
    (r'C:\music\song.flac', True),
    (r'C:\music', True),
    (r'C:\CONFIG\a.flac', True),
    (r'\\server\share\a.flac', True),
    (r'C:\a<b>.flac', False),
    (r'C:\a|b.flac', False),
    (r'C:\a:b.flac', False),
    (r'C:\CON.txt', False),
    (r'C:\NUL', False),
    (r'C:\COM1.txt', False),
])
def test_verify_path_format_windows(monkeypatch, raw, expected):
    monkeypatch.setattr(os, 'name', 'nt')
    assert verify_path_format(raw) is expected


def test_verify_path_format_posix_ignores_windows_rules(monkeypatch):
    monkeypatch.setattr(os, 'name', 'posix')
    assert verify_path_format(r'C:\a<b>.flac') is True
    assert verify_path_format('/music/song.flac') is True
    assert verify_path_format('') is False


def test_box_single_line():
    lines = box('hello').split('\n')
    assert len(lines) == 3                      # top + content + bottom
    assert lines[0] == '/=========\\'            # 9 horizontals = 5 + 2+2 padding
    assert lines[1] == '|  hello  |'
    assert lines[2] == '\\=========/'


def test_box_multiple_lines_pads_to_max_width():
    lines = box('a\nlonger').split('\n')
    assert lines[0] == '/==========\\'
    assert lines[1] == '|  a       |'           # padded to 'longer' width
    assert lines[2] == '|  longer  |'
    assert lines[3] == '\\==========/'


def test_box_padding_arguments():
    lines = box('hi', l_pad=0, r_pad=0).split('\n')
    assert lines[0] == '/==\\'                  # 2 horizontals = 2 content + 0+0
    assert lines[1] == '|hi|'
    assert lines[2] == '\\==/'


def test_box_cjk_width_uses_display_columns():
    # '中' is 2 display columns wide but 1 char; box must pad by display width
    lines = box('中\nab', l_pad=0, r_pad=0).split('\n')
    assert lines[1] == '|中|'
    assert lines[2] == '|ab|'


def test_box_style_parameter():
    lines = box('hi', l_pad=0, r_pad=0, style='double').split('\n')
    assert lines[0] == '╔══╗'
    assert lines[1] == '║hi║'
    assert lines[2] == '╚══╝'


def test_box_multiple_texts_side_by_side():
    lines = box('ab', 'cd', l_pad=1, r_pad=1, style='rounded').split('\n')
    assert lines[0] == '╭────┬────╮'            # two columns joined by ┬
    assert lines[1] == '│ ab │ cd │'
    assert lines[2] == '╰────┴────╯'            # bottom joined by ┴


def test_box_multiple_texts_uneven_heights():
    lines = box('a\nb', 'c', l_pad=1, r_pad=1, style='square').split('\n')
    assert lines[0] == '┌───┬───┐'
    assert lines[1] == '│ a │ c │'
    assert lines[2] == '│ b │   │'              # shorter column padded with blank
    assert lines[3] == '└───┴───┘'


def test_center_pads_evenly():
    assert center('ab', 6) == '  ab  '
    assert center('a', 4) == '  a '             # ceil on left: 2, floor on right: 1
    assert center('x' * 6, 4) == 'xxxxxx'       # wider than target: unchanged


def test_get_lyric_line_returns_index_or_sentinel():
    from src.utils import get_lyric_line, parse_lyric
    from src.sentinels import SENTINELS
    import tempfile, os
    lrc = '[00:01.00]one\n[00:02.00]two\n[00:03.00]three\n'
    path = os.path.join(tempfile.gettempdir(), 'test_lyric_line.lrc')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(lrc)
    lyric = parse_lyric(path)
    assert get_lyric_line(lyric, 0) is SENTINELS.BEFORE_FIRST_LYRIC
    assert get_lyric_line(lyric, 1000) == 0     # exactly at first line
    assert get_lyric_line(lyric, 1500) == 0     # between line 1 and 2
    assert get_lyric_line(lyric, 2500) == 1
    assert get_lyric_line(lyric, 99999) == 2    # after last line -> last index
    assert get_lyric_line([], 1000) is None     # empty


def test_window_list_newline_selected():
    from src.utils import window_list
    lines = ['a', 'b', 'c', 'd', 'e']
    result = window_list(lines, 3, 2, newline_selected=True, mark_unshown=False, left_align=False)
    joined = '\n'.join(result)
    assert '\n-[ c ]-\n' in joined             # selected gets leading/trailing blank lines
    assert '↑' not in joined and '↓' not in joined  # mark_unshown=False


def test_window_list_mark_unshown_counts():
    from src.utils import window_list
    lines = [str(i) for i in range(20)]
    result = window_list(lines, 5, 10)         # defaults: mark_unshown=True, left_align=True
    joined = '\n'.join(result)
    assert '↑' in joined and '↓' in joined
    # selected line is marked
    assert '-[ 10 ]-' in joined
