import os

from pathlib import Path


# Keys every poll response must carry. A subset check is used so adding a new
# field does not break this test, while renaming or dropping one does.
POLL_KEYS = {
    'id', 'path', 'name', 'artist', 'album',
    'duration', 'bitrate', 'sample_rate', 'channels', 'lyric_path',
    'in_library', 'player_status', 'volume', 'mute', 'shuffle', 'loop',
    'online_lyric', 'playlist_len', 'current_num', 'run_time',
    'length', 'time', 'dev',
    'aliases', 'added_playlists',
    'lyric', 'lyric_loading', 'lyric_offset', 'offset_overlay',
    'current_songs', 'playlists',
}


def _request(backend, action, **extra):
    request = {'action': action, 'cwd': os.getcwd()}
    request.update(extra)
    return backend.dispatch(request)


def _poll(backend):
    response = _request(backend, 'poll')
    assert response['code'] == 0
    return response['attachment']


def test_poll_needs_no_cwd(backend):
    """Polling frontends (dash, tray, lyric) do not send cwd."""
    response = backend.dispatch({'action': 'poll', 'source': 'dash'})
    assert response['code'] == 0


def test_poll_before_open(backend):
    attachment = _poll(backend)
    assert POLL_KEYS <= set(attachment.keys())

    assert attachment['id'] is None
    assert attachment['path'] is None
    assert attachment['in_library'] is False
    assert attachment['playlist_len'] is None
    assert attachment['current_num'] is None
    assert attachment['current_songs'] == []

    assert attachment['aliases'] is None
    assert attachment['added_playlists'] is None

    assert attachment['lyric'] is None
    assert attachment['lyric_loading'] is False
    assert attachment['lyric_offset'] == 0
    assert attachment['offset_overlay'] == 0


def test_poll_current_song_in_library(backend, audio_file):
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'lib.playlist.create', name='work')['code'] == 0
    assert _request(backend, 'lib.playlist.add', playlist='work', songs=[audio_file])['code'] == 0
    song_id = backend.database.get_song_via_path(audio_file)
    assert song_id is not None
    assert _request(backend, 'open', song=audio_file)['code'] == 0

    attachment = _poll(backend)
    assert attachment['id'] == song_id
    assert attachment['path'] == audio_file
    assert attachment['in_library'] is True
    assert attachment['aliases'] == ['test_audio']
    assert attachment['added_playlists'] == ['work']
    assert attachment['playlists'] == ['work']
    assert attachment['playlist_len'] == 1
    assert attachment['current_num'] == 0 # 0-based
    assert attachment['player_status'] in ('playing', 'paused')
    assert attachment['duration'] == 3000
    assert attachment['length'] > 0

    assert len(attachment['current_songs']) == 1
    assert attachment['current_songs'][0]['id'] == song_id
    assert attachment['current_songs'][0]['path'] == audio_file


def test_poll_current_song_not_in_library(backend, audio_file):
    """A song opened from outside the library still yields a usable snapshot."""
    assert _request(backend, 'open', song=audio_file)['code'] == 0

    attachment = _poll(backend)
    assert attachment['id'] is None
    assert attachment['path'] == audio_file
    assert attachment['in_library'] is False
    assert attachment['aliases'] is None
    assert attachment['added_playlists'] is None
    assert attachment['playlist_len'] == 1
    assert attachment['current_num'] == 0
    assert attachment['current_songs'] == [{'path': audio_file}]


def test_poll_serves_parsed_lyric(backend, audio_file):
    """`lib add` binds the same-name .lrc, poll serves the parsed pairs."""
    lyric_path = Path(audio_file).with_suffix('.lrc')
    lyric_path.write_text('[00:01.00]hello\n[00:05.00]world\n', encoding='utf-8')
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'open', song=audio_file)['code'] == 0

    attachment = _poll(backend)
    assert attachment['lyric_path'] == str(lyric_path)
    assert attachment['lyric'] == [[1000, 'hello'], [5000, 'world']]
    assert attachment['lyric_loading'] is False
    assert attachment['lyric_offset'] == 0


def test_poll_song_without_lyric(backend, audio_file):
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'open', song=audio_file)['code'] == 0

    attachment = _poll(backend)
    assert attachment['lyric_path'] is None
    assert attachment['lyric'] is None
    assert attachment['lyric_loading'] is False


def test_poll_reflects_playback_controls(backend, audio_file):
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'open', song=audio_file)['code'] == 0
    assert _poll(backend)['volume'] == 100

    assert _request(backend, 'volume', volume='42')['code'] == 0
    assert _request(backend, 'mute')['code'] == 0
    assert _request(backend, 'shuffle')['code'] == 0
    assert _request(backend, 'loop')['code'] == 0

    attachment = _poll(backend)
    assert attachment['volume'] == 42
    assert attachment['mute'] is True
    assert attachment['shuffle'] is True
    assert attachment['loop'] is True


def test_poll_after_stop_keeps_current_playlist(backend, audio_file):
    """Stopping resets the player, not the playlist the frontend browses."""
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'open', song=audio_file)['code'] == 0
    assert _request(backend, 'stop')['code'] == 0

    attachment = _poll(backend)
    assert attachment['player_status'] == 'stopped'
    assert attachment['playlist_len'] == 1
    assert attachment['current_num'] == 0
    assert len(attachment['current_songs']) == 1


def test_reload_refreshes_per_song_lyric_offset(backend, audio_file):
    """A library write reaches the playing song's snapshot only after a reload.

    The in-memory song info is a snapshot taken when the song was opened, so
    `lib.lyric.offset` alone does not move `lyric_offset`; loading the last
    song again re-reads the song from the library.
    """
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'open', song=audio_file)['code'] == 0
    assert _request(backend, 'lib.lyric.offset', song=audio_file, offset=-250)['code'] == 0
    assert backend.database.get_song_meta(1, 'offset') == -250
    assert _poll(backend)['lyric_offset'] == 0

    assert _request(backend, 'load_last')['code'] == 0
    assert _poll(backend)['lyric_offset'] == -250


def test_reload_refreshes_metadata(backend, audio_file):
    assert _request(backend, 'lib.add', paths=[audio_file])['code'] == 0
    assert _request(backend, 'open', song=audio_file)['code'] == 0
    assert _request(backend, 'lib.meta.set', song=audio_file, name='Renamed')['code'] == 0
    assert backend.database.get_song_info(1)[0]['name'] == 'Renamed'
    assert _poll(backend)['name'] is None

    assert _request(backend, 'load_last')['code'] == 0
    assert _poll(backend)['name'] == 'Renamed'


def test_reload_keeps_play_all_playlist(backend, audio_file, tmp_path):
    """Reloading a play-all session re-reads the library and keeps the list."""
    second = str(tmp_path / 'second.wav')
    with open(audio_file, 'rb') as source:
        audio = source.read()
    with open(second, 'wb') as target:
        target.write(audio)

    assert _request(backend, 'lib.add', paths=[audio_file, second])['code'] == 0
    assert _request(backend, 'play-all')['code'] == 0
    assert _poll(backend)['playlist_len'] == 2

    assert _request(backend, 'load_last')['code'] == 0
    attachment = _poll(backend)
    assert attachment['playlist_len'] == 2
    assert len(attachment['current_songs']) == 2
