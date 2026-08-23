import os

import pytest

from src.utils import verify_path_format


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
