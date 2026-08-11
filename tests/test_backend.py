import os
import wave

import pytest

from src.sentinels import SENTINELS


def _request(backend, action, **extra):
    request = {'action': action, 'cwd': os.getcwd()}
    request.update(extra)
    return backend.dispatch(request)


def test_status_before_open(backend):
    response = _request(backend, 'status')
    assert response['code'] == 0
    assert response['attachment']['path'] == 'none'
    assert response['attachment']['in_library'] is False


def test_status_missing_cwd(backend):
    # cwd validation now lives inside actions that need it (open/lib.*),
    # not at the global dispatch gate; status never needs cwd.
    response = _request(backend, 'status')
    assert response['code'] == 0


def test_invalid_action(backend):
    response = _request(backend, 'bogus')
    assert response['code'] == 1
    assert 'invalid action' in response['msg']


def test_missing_action_key(backend):
    response = backend.dispatch({'cwd': os.getcwd()})
    assert response['code'] == 1
    assert 'action' in response['msg']


def test_missing_required_key(backend):
    response = _request(backend, 'open')
    assert response['code'] == 1
    assert 'song' in response['msg']


def test_guards_before_open(backend):
    assert _request(backend, 'pause')['code'] == 1
    assert _request(backend, 'resume')['code'] == 1
    assert _request(backend, 'toggle')['code'] == 1


def test_list_before_open(backend):
    response = _request(backend, 'list')
    assert response['code'] == 0
    assert response['attachment'] == []


def test_list_after_open_raw_path(backend, audio_file):
    _request(backend, 'open', song=audio_file)
    response = _request(backend, 'list')
    assert response['code'] == 0
    assert response['attachment'] == [{'path': audio_file}]


def test_list_after_open_lib_song(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'open', song=audio_file)
    response = _request(backend, 'list')
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['id'] == 1
    assert response['attachment'][0]['path'] == audio_file


def test_list_after_open_playlist(backend, audio_file):
    _create_playlist_with_song(backend, audio_file, 'workout')
    _request(backend, 'open', song='workout')
    response = _request(backend, 'list')
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['path'] == audio_file


def test_switch_missing_number(backend):
    response = _request(backend, 'switch')
    assert response['code'] == 1
    assert 'number' in response['msg']


def test_switch_before_open(backend):
    response = _request(backend, 'switch', number=1)
    assert response['code'] == 1
    assert 'no songs are being played' in response['msg']


def _open_two_song_playlist(backend, audio_file, tmp_path):
    """Open a playlist with two songs sorted as [a, b] by basename."""
    first = audio_file
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    _open_playlist_with_songs(backend, [first, second], 'pair')
    return first, second


def test_switch_to_number(backend, audio_file, tmp_path):
    first, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    response = _request(backend, 'switch', number=1)
    assert response['code'] == 0
    assert backend.current_song_num == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == first

    response = _request(backend, 'switch', number=2)
    assert response['code'] == 0
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


def test_switch_zero_means_first(backend, audio_file, tmp_path):
    first, _ = _open_two_song_playlist(backend, audio_file, tmp_path)
    response = _request(backend, 'switch', number=0)
    assert response['code'] == 0
    assert backend.current_song_num == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == first


def test_switch_too_large_goes_to_last(backend, audio_file, tmp_path):
    _, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    response = _request(backend, 'switch', number=999999)
    assert response['code'] == 0
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


def test_switch_negative_counts_from_last(backend, audio_file, tmp_path):
    first, second = _open_two_song_playlist(backend, audio_file, tmp_path)

    response = _request(backend, 'switch', number=-1)
    assert response['code'] == 0
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second

    response = _request(backend, 'switch', number=-2)
    assert response['code'] == 0
    assert backend.current_song_num == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == first


def test_switch_negative_too_large_goes_to_first(backend, audio_file, tmp_path):
    first, _ = _open_two_song_playlist(backend, audio_file, tmp_path)
    response = _request(backend, 'switch', number=-999)
    assert response['code'] == 0
    assert backend.current_song_num == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == first


def test_open_raw_path(backend, audio_file):
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    assert backend.current_song_in_lib is False
    status = _request(backend, 'status')
    assert status['attachment']['path'] == audio_file


def test_open_missing_file(backend):
    response = _request(backend, 'open', song='nonexistent_song.flac')
    assert response['code'] == 1
    assert 'valid and existing path' in response['msg']


def test_open_via_library_path(backend, audio_file):
    database = backend.database
    database.add_song(audio_file)
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    assert backend.current_song_in_lib is True


def test_open_via_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    response = _request(backend, 'open', song='test_alias')
    assert response['code'] == 0
    assert backend.current_song_in_lib is True
    assert backend.current_song_info[0]['path'] == audio_file


def test_open_alias_priority_over_path(backend, audio_file, tmp_path):
    """Alias lookup must win even if the alias string is not a real path."""
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    response = _request(backend, 'open', song='test_alias')
    assert response['code'] == 0
    assert backend.current_song_info[0]['id'] == song_id


def test_lib_add(backend, audio_file):
    response = _request(backend, 'lib.add', path=audio_file)
    assert response['code'] == 0
    assert backend.database.song_exists(1)


def test_lib_add_duplicate(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.add', path=audio_file)
    assert response['code'] == 1
    assert 'already exists' in response['msg']


def test_lib_add_missing_file(backend):
    response = _request(backend, 'lib.add', path=r'C:\does\not\exist.flac')
    assert response['code'] == 1
    assert 'valid and existing path' in response['msg']


def test_lib_list_empty(backend):
    response = _request(backend, 'lib.list', show_aliases=False)
    assert response['code'] == 0
    assert response['attachment'] == []


def test_lib_list_after_add(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.list', show_aliases=False)
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['path'] == audio_file
    assert 'aliases' not in response['attachment'][0]


def test_lib_list_with_show_aliases(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    response = _request(backend, 'lib.list', show_aliases=True)
    assert response['code'] == 0
    assert response['attachment'][0]['aliases'] == ['favorite']


def test_lib_list_show_aliases_empty(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.list', show_aliases=True)
    assert response['code'] == 0
    assert response['attachment'][0]['aliases'] == []


def test_lib_del_by_path(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.del', song=audio_file)
    assert response['code'] == 0
    assert backend.database.song_exists(1) is False


def test_lib_del_by_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    response = _request(backend, 'lib.del', song='test_alias')
    assert response['code'] == 0
    assert backend.database.song_exists(song_id) is False


def test_lib_del_not_in_library(backend):
    response = _request(backend, 'lib.del', song='ghost_song')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_del_when_nothing_open(backend, audio_file):
    """Deleting a lib song while nothing is open must not crash (regression: Path(None))."""
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.del', song=audio_file)
    assert response['code'] == 0


def test_lib_del_current_song_resets_state(backend, audio_file):
    """Deleting the currently-open lib song must flip in_library back to False."""
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'open', song=audio_file)
    assert backend.current_song_in_lib is True

    response = _request(backend, 'lib.del', song=audio_file)
    assert response['code'] == 0
    assert backend.current_song_in_lib is False
    assert backend.current_song_info[0] == {'path': audio_file}


def test_lib_del_cascades_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    _request(backend, 'lib.del', song=audio_file)
    assert database.get_song_via_alias('test_alias') is SENTINELS.ALIAS_NOT_FOUND


def test_lib_alias_bind(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    assert response['code'] == 0
    assert backend.database.get_song_via_alias('favorite') == 1


def test_lib_alias_bind_duplicate(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    response = _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    assert response['code'] == 1
    assert 'already' in response['msg']


def test_lib_alias_bind_missing_song(backend):
    response = _request(backend, 'lib.alias.bind', song='ghost_song', alias='favorite')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_alias_list(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    _request(backend, 'lib.alias.bind', song=audio_file, alias='workout')
    response = _request(backend, 'lib.alias.list', song=audio_file)
    assert response['code'] == 0
    assert response['attachment'] == ['favorite', 'workout']


def test_lib_alias_list_missing_song(backend):
    response = _request(backend, 'lib.alias.list', song='ghost_song')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_alias_del(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    response = _request(backend, 'lib.alias.unbind', alias='favorite')
    assert response['code'] == 0
    assert backend.database.get_song_via_alias('favorite') is SENTINELS.ALIAS_NOT_FOUND


def test_lib_alias_del_keeps_song(backend, audio_file):
    """Deleting an alias must not delete the song it was bound to."""
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    _request(backend, 'lib.alias.unbind', alias='favorite')
    assert backend.database.get_song_via_path(audio_file) == 1


def test_lib_alias_del_not_exist(backend):
    response = _request(backend, 'lib.alias.unbind', alias='ghost_alias')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def _create_playlist_with_song(backend, audio_file, playlist_name):
    """Seed a song + playlist + playlist membership for playlist tests."""
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    playlist_id = database.create_playlist(playlist_name)[0]
    database.add_song_to_playlist(playlist_id, song_id)
    return song_id, playlist_id


def _make_wav(path):
    """Write a short silent WAV file (mirrors the conftest audio_file fixture)."""
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b'\x00\x00' * (8000 * 3))


def _open_playlist_with_songs(backend, paths, playlist_name):
    """Seed a playlist from existing files and open it."""
    database = backend.database
    playlist_id = database.create_playlist(playlist_name)[0]
    for path in paths:
        song_id, _ = database.add_song(path)
        database.add_song_to_playlist(playlist_id, song_id)
    response = _request(backend, 'open', song=playlist_name)
    assert response['code'] == 0


def test_lib_playlist_kick(backend, audio_file):
    song_id, playlist_id = _create_playlist_with_song(backend, audio_file, 'workout')
    response = _request(backend, 'lib.playlist.kick', song=audio_file, playlist='workout')
    assert response['code'] == 0
    assert backend.database.get_playlist_songs(playlist_id) is SENTINELS.PLAYLIST_EMPTY
    assert backend.database.song_exists(song_id)


def test_lib_playlist_kick_by_alias(backend, audio_file):
    database = backend.database
    song_id, playlist_id = _create_playlist_with_song(backend, audio_file, 'workout')
    database.bind_alias(song_id, 'workout_song')
    response = _request(backend, 'lib.playlist.kick', song='workout_song', playlist='workout')
    assert response['code'] == 0
    assert backend.database.get_playlist_songs(playlist_id) is SENTINELS.PLAYLIST_EMPTY


def test_lib_playlist_kick_song_not_in_playlist(backend, audio_file):
    _create_playlist_with_song(backend, audio_file, 'workout')
    other_file = audio_file.replace('test_audio', 'test_other')
    song_id, _ = backend.database.add_song(other_file)
    response = _request(backend, 'lib.playlist.kick', song=other_file, playlist='workout')
    assert response['code'] == 1
    assert 'not in the playlist' in response['msg']
    assert backend.database.song_exists(song_id)


def test_lib_playlist_kick_song_not_in_library(backend):
    _request(backend, 'lib.playlist.create', name='workout')
    response = _request(backend, 'lib.playlist.kick', song='ghost_song', playlist='workout')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_playlist_kick_playlist_not_found(backend, audio_file):
    response = _request(backend, 'lib.playlist.kick', song=audio_file, playlist='ghost_playlist')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_playlist_del(backend):
    _request(backend, 'lib.playlist.create', name='workout')
    response = _request(backend, 'lib.playlist.del', playlist='workout')
    assert response['code'] == 0
    assert backend.database.get_playlist_via_name('workout') is SENTINELS.PLAYLIST_NOT_FOUND


def test_lib_playlist_del_cascades_membership(backend, audio_file):
    _create_playlist_with_song(backend, audio_file, 'workout')
    response = _request(backend, 'lib.playlist.del', playlist='workout')
    assert response['code'] == 0
    assert backend.database.get_all_playlists() == []


def test_lib_playlist_del_playlist_not_found(backend):
    response = _request(backend, 'lib.playlist.del', playlist='ghost_playlist')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_playlist_del_missing_key(backend):
    response = _request(backend, 'lib.playlist.del')
    assert response['code'] == 1
    assert 'playlist' in response['msg']


def test_restart_before_open(backend):
    response = _request(backend, 'restart')
    assert response['code'] == 1
    assert 'neither playing nor paused' in response['msg']


def test_restart_after_open(backend, audio_file):
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    response = _request(backend, 'restart')
    assert response['code'] == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == audio_file


def test_restart_clears_memorized_pos(backend, audio_file):
    database = backend.database
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    database.set_pos(audio_file, 1000)
    assert database.get_pos(audio_file) == 1000

    response = _request(backend, 'restart')
    assert response['code'] == 0
    assert database.get_pos(audio_file) is SENTINELS.POS_NOT_FOUND


def test_lib_meta_set_name(backend, audio_file):
    song_id, _ = backend.database.add_song(audio_file)
    response = _request(backend, 'lib.meta.set', song=audio_file, name='Foo')
    assert response['code'] == 0
    assert backend.database.get_song_meta(song_id, 'name') == 'Foo'


def test_lib_meta_set_multiple_fields(backend, audio_file):
    song_id, _ = backend.database.add_song(audio_file)
    response = _request(backend, 'lib.meta.set', song=audio_file,
                        name='Foo', artist='Bar', album='Baz')
    assert response['code'] == 0
    assert backend.database.get_song_meta(song_id, 'name') == 'Foo'
    assert backend.database.get_song_meta(song_id, 'artist') == 'Bar'
    assert backend.database.get_song_meta(song_id, 'album') == 'Baz'


def test_lib_meta_set_by_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'my_song')
    response = _request(backend, 'lib.meta.set', song='my_song', artist='Bar')
    assert response['code'] == 0
    assert database.get_song_meta(song_id, 'artist') == 'Bar'


def test_lib_meta_set_clear(backend, audio_file):
    song_id, _ = backend.database.add_song(audio_file)
    backend.database.set_song_meta(song_id, 'name', 'Foo')
    assert backend.database.get_song_meta(song_id, 'name') == 'Foo'

    response = _request(backend, 'lib.meta.set', song=audio_file, name='')
    assert response['code'] == 0
    assert backend.database.get_song_meta(song_id, 'name') is None


def test_lib_meta_set_no_metadata_given(backend, audio_file):
    backend.database.add_song(audio_file)
    response = _request(backend, 'lib.meta.set', song=audio_file)
    assert response['code'] == 1
    assert 'no metadata was given' in response['msg']


def test_lib_meta_set_song_not_in_library(backend):
    response = _request(backend, 'lib.meta.set', song='ghost_song', name='Foo')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_meta_set_missing_song_key(backend):
    response = _request(backend, 'lib.meta.set', name='Foo')
    assert response['code'] == 1
    assert 'song' in response['msg']
