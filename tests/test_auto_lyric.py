import os

def _request(backend, action, **kwargs):
    kwargs['action'] = action
    return backend.dispatch(kwargs)

def test_auto_lyric_on_add(backend, tmp_path, monkeypatch):
    # create fake audio + same-name .lrc
    audio = tmp_path / 'song.mp3'
    audio.write_bytes(b'ID3fake')
    lrc = tmp_path / 'song.lrc'
    lrc.write_text('[00:01.00]hello\n[00:05.00]world\n', encoding='utf-8')

    response = _request(backend, 'lib.add', paths=[str(audio)], cwd=str(tmp_path))
    assert response['code'] == 0

    song_id = backend.database.get_song_via_path(str(audio))
    assert song_id is not None
    lyric = backend.database.get_song_meta(song_id, 'lyric')
    assert lyric == str(lrc)

def test_auto_lyric_skipped_with_flag(backend, tmp_path):
    audio = tmp_path / 'song2.mp3'
    audio.write_bytes(b'ID3fake')
    lrc = tmp_path / 'song2.lrc'
    lrc.write_text('[00:01.00]hello\n', encoding='utf-8')

    response = _request(backend, 'lib.add', paths=[str(audio)], cwd=str(tmp_path), skip_lyric=True)
    assert response['code'] == 0

    song_id = backend.database.get_song_via_path(str(audio))
    lyric = backend.database.get_song_meta(song_id, 'lyric')
    assert lyric is None

def test_auto_lyric_no_lrc_file(backend, tmp_path):
    audio = tmp_path / 'song3.mp3'
    audio.write_bytes(b'ID3fake')

    response = _request(backend, 'lib.add', paths=[str(audio)], cwd=str(tmp_path))
    assert response['code'] == 0

    song_id = backend.database.get_song_via_path(str(audio))
    lyric = backend.database.get_song_meta(song_id, 'lyric')
    assert lyric is None

def test_auto_lyric_not_affected_by_skip_alias(backend, tmp_path):
    # regression: set_lyric was copied from skip_alias in lib.add (bug)
    audio = tmp_path / 'song4.mp3'
    audio.write_bytes(b'ID3fake')
    lrc = tmp_path / 'song4.lrc'
    lrc.write_text('[00:01.00]hello\n', encoding='utf-8')

    response = _request(backend, 'lib.add', paths=[str(audio)], cwd=str(tmp_path), skip_alias=True)
    assert response['code'] == 0

    song_id = backend.database.get_song_via_path(str(audio))
    lyric = backend.database.get_song_meta(song_id, 'lyric')
    assert lyric == str(lrc)
