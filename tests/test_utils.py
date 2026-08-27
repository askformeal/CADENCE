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
    assert len(lines) == 4                      # top + spacer + content + bottom
    assert lines[0] == ' _________ '            # 9 underscores = 5 + 2+2 padding
    assert lines[1] == '/         \\'
    assert lines[2] == '|  hello  |'
    assert lines[3] == '\\_________/'


def test_box_multiple_lines_pads_to_max_width():
    lines = box('a\nlonger').split('\n')
    assert lines[2] == '|  a       |'           # padded to 'longer' width
    assert lines[3] == '|  longer  |'
    assert lines[4] == '\\__________/'


def test_box_padding_arguments():
    lines = box('hi', l_pad=2, r_pad=3).split('\n')
    assert lines[0] == ' ___________ '          # 11 underscores = 2+2+3+4
    assert lines[2] == '|    hi     |'          # 2 left + content + 3 right
    assert lines[3] == '\\___________/'


def test_box_cjk_width_uses_display_columns():
    # '中' is 2 display columns wide but 1 char; box must pad by display width
    lines = box('中\nab').split('\n')
    assert lines[2] == '|  中  |'
    assert lines[3] == '|  ab  |'


def test_center_pads_evenly():
    assert center('ab', 6) == '  ab  '
    assert center('a', 4) == '  a '             # ceil on left: 2, floor on right: 1
    assert center('x' * 6, 4) == 'xxxxxx'       # wider than target: unchanged
