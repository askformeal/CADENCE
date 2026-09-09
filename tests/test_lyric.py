import os

from src.sentinels import SENTINELS


def _request(backend, action, **extra):
    request = {'action': action, 'cwd': os.getcwd()}
    request.update(extra)
    return backend.dispatch(request)


def _open_raw(backend, audio_file):
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    assert backend.playback.current_song_in_lib is False


def test_get_lyric_returns_offset_overlay_before_open(backend):
    """get_lyric must not crash and should attach offset_overlay even with no song.

    Guards the AttributeError regression where the handler read the
    non-existent ctx.playback.lyric_overlay attribute.
    """
    response = _request(backend, 'get_lyric')
    assert response['code'] == 0
    assert 'offset_overlay' in response['attachment']
    assert response['attachment']['offset_overlay'] == 0


def test_get_lyric_after_open_has_offset_overlay(backend, audio_file):
    _open_raw(backend, audio_file)
    response = _request(backend, 'get_lyric')
    assert response['code'] == 0
    assert response['attachment']['offset_overlay'] == 0


def test_set_offset_overlay_sets_value(backend, audio_file):
    _open_raw(backend, audio_file)
    response = _request(backend, 'set_offset_overlay', offset=500)
    assert response['code'] == 0
    assert backend.playback.offset_overlay == 500

    # and the next get_lyric serves that overlay
    lyric = _request(backend, 'get_lyric')
    assert lyric['attachment']['offset_overlay'] == 500


def test_set_offset_overlay_autoincrement_accumulates(backend, audio_file):
    _open_raw(backend, audio_file)
    _request(backend, 'set_offset_overlay', offset=300)
    _request(backend, 'set_offset_overlay', autoincrement=True, offset=100)
    assert backend.playback.offset_overlay == 400


def test_set_offset_overlay_autoincrement_decrements(backend, audio_file):
    _open_raw(backend, audio_file)
    _request(backend, 'set_offset_overlay', offset=200)
    _request(backend, 'set_offset_overlay', autoincrement=True, offset=-100)
    assert backend.playback.offset_overlay == 100


def test_set_offset_overlay_overwrites_when_not_autoincrement(backend, audio_file):
    _open_raw(backend, audio_file)
    _request(backend, 'set_offset_overlay', offset=200)
    # autoincrement defaults False -> set, not accumulate
    _request(backend, 'set_offset_overlay', offset=50)
    assert backend.playback.offset_overlay == 50


def test_set_offset_overlay_missing_offset_key(backend):
    response = _request(backend, 'set_offset_overlay')
    assert response['code'] == 1
    assert 'offset' in response['msg']
