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
    assert response['attachment']['path'] is None
    assert response['attachment']['in_library'] is False


def test_status_missing_cwd(backend):
    # cwd validation now lives inside actions that need it (open/lib.*),
    # not at the global dispatch gate; status never needs cwd.
    response = _request(backend, 'status')
    assert response['code'] == 0


def test_invalid_action(backend):
    response = _request(backend, 'bogus')
    assert response['code'] == 1
    assert 'unknown action received: "bogus"' in response['msg']


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
    _request(backend, 'lib.add', paths=[audio_file])
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


def test_dice_before_open(backend):
    response = _request(backend, 'dice')
    assert response['code'] == 1
    assert 'no songs are being played' in response['msg']


def test_dice_single_song(backend, audio_file):
    _request(backend, 'open', song=audio_file)
    response = _request(backend, 'dice')
    assert response['code'] == 1
    assert 'only one song' in response['msg']


def _open_three_song_playlist(backend, audio_file, tmp_path):
    """Open a playlist with three songs sorted as [a, b, c] by basename."""
    first = audio_file
    second = str(tmp_path / 'test_b.wav')
    third = str(tmp_path / 'test_c.wav')
    _make_wav(second)
    _make_wav(third)
    _open_playlist_with_songs(backend, [first, second, third], 'trio')
    return first, second, third


def test_dice_skips_current_song(backend, audio_file, tmp_path, monkeypatch):
    _, second, _ = _open_three_song_playlist(backend, audio_file, tmp_path)
    assert backend.current_song_num == 0

    pool_seen = []
    def fake_choice(seq):
        pool_seen.extend(seq)
        return seq[0]
    monkeypatch.setattr('src.backend.random.choice', fake_choice)

    response = _request(backend, 'dice')
    assert response['code'] == 0
    assert pool_seen == [1, 2]  # current song (0) excluded from the pool
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


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
    response = _request(backend, 'lib.add', paths=[audio_file])
    assert response['code'] == 0
    assert backend.database.song_exists(1)


def test_lib_add_duplicate(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.add', paths=[audio_file])
    assert response['code'] == 1
    assert 'already exists' in response['failed'][0]['msg']


def test_lib_add_missing_file(backend):
    response = _request(backend, 'lib.add', paths=[r'C:\does\not\exist.flac'])
    assert response['code'] == 1
    assert 'valid and existing path' in response['failed'][0]['msg']


def test_lib_add_batch_multiple(backend, tmp_path):
    _make_wav(tmp_path / 'a.wav')
    _make_wav(tmp_path / 'b.wav')
    response = _request(backend, 'lib.add', paths=[str(tmp_path / 'a.wav'), str(tmp_path / 'b.wav')])
    assert response['code'] == 0
    assert '2/2' in response['msg']
    assert backend.database.song_exists(1)
    assert backend.database.song_exists(2)


def test_lib_add_batch_partial_failure(backend, tmp_path):
    _make_wav(tmp_path / 'a.wav')
    response = _request(backend, 'lib.add', paths=[str(tmp_path / 'a.wav'), r'C:\does\not\exist.flac'])
    assert response['code'] == 0
    assert '1/2' in response['msg']
    assert len(response['failed']) == 1
    assert 'valid and existing path' in response['failed'][0]['msg']


def test_lib_add_batch_all_failed(backend):
    response = _request(backend, 'lib.add', paths=[r'C:\does\not\exist1.flac', r'C:\does\not\exist2.flac'])
    assert response['code'] == 1
    assert '0/2' in response['msg']
    assert len(response['failed']) == 2


def test_lib_add_batch_empty_paths(backend):
    response = _request(backend, 'lib.add', paths=[])
    assert response['code'] == 1
    assert 'empty list of paths' in response['msg']


def test_lib_add_batch_alias_mismatch(backend, tmp_path):
    _make_wav(tmp_path / 'a.wav')
    _make_wav(tmp_path / 'b.wav')
    response = _request(backend, 'lib.add', paths=[str(tmp_path / 'a.wav'), str(tmp_path / 'b.wav')], aliases=['only_one'])
    assert response['code'] == 1
    assert 'not the same' in response['msg']


def test_lib_add_batch_with_aliases(backend, tmp_path):
    _make_wav(tmp_path / 'a.wav')
    _make_wav(tmp_path / 'b.wav')
    response = _request(backend, 'lib.add', paths=[str(tmp_path / 'a.wav'), str(tmp_path / 'b.wav')], aliases=['alpha', 'beta'])
    assert response['code'] == 0
    assert '2/2' in response['msg']
    assert backend.database.get_song_via_alias('alpha') == 1
    assert backend.database.get_song_via_alias('beta') == 2


def test_lib_list_empty(backend):
    response = _request(backend, 'lib.list', show_aliases=False)
    assert response['code'] == 0
    assert response['attachment'] == []


def test_lib_list_after_add(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.list', show_aliases=False)
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['path'] == audio_file
    assert 'aliases' not in response['attachment'][0]


def test_lib_list_with_show_aliases(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    response = _request(backend, 'lib.list', show_aliases=True)
    assert response['code'] == 0
    assert response['attachment'][0]['aliases'] == ['test_audio', 'favorite']


def test_lib_list_show_aliases_empty(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file], skip_alias=True)
    response = _request(backend, 'lib.list', show_aliases=True)
    assert response['code'] == 0
    assert response['attachment'][0]['aliases'] == []


def test_lib_list_with_show_playlists(backend, audio_file):
    database = backend.database
    _request(backend, 'lib.add', paths=[audio_file])
    song_id = database.get_all_song_info()[0]['id']
    playlist_id, _ = database.create_playlist('workout')
    database.add_song_to_playlist(playlist_id, song_id)
    response = _request(backend, 'lib.list', show_playlists=True)
    assert response['code'] == 0
    assert response['attachment'][0]['playlists'] == ['workout']


def test_lib_list_show_playlists_empty(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.list', show_playlists=True)
    assert response['code'] == 0
    assert response['attachment'][0]['playlists'] == []


def test_lib_list_without_show_playlists(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.list')
    assert response['code'] == 0
    assert 'playlists' not in response['attachment'][0]


def test_lib_del_by_path(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.del', songs=[audio_file])
    assert response['code'] == 0
    assert backend.database.song_exists(1) is False


def test_lib_del_by_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    response = _request(backend, 'lib.del', songs=['test_alias'])
    assert response['code'] == 0
    assert backend.database.song_exists(song_id) is False


def test_lib_del_not_in_library(backend):
    response = _request(backend, 'lib.del', songs=['ghost_song'])
    assert response['code'] == 1
    assert 'does not exist' in response['failed'][0]['msg']


def test_lib_del_when_nothing_open(backend, audio_file):
    """Deleting a lib song while nothing is open must not crash (regression: Path(None))."""
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.del', songs=[audio_file])
    assert response['code'] == 0


def test_lib_del_current_song_resets_state(backend, audio_file):
    """Deleting the currently-open lib song must flip in_library back to False."""
    _request(backend, 'lib.add', paths=[audio_file])
    _request(backend, 'open', song=audio_file)
    assert backend.current_song_in_lib is True

    response = _request(backend, 'lib.del', songs=[audio_file])
    assert response['code'] == 0
    assert backend.current_song_in_lib is False
    assert backend.current_song_info[0] == {'path': audio_file}


def test_lib_del_cascades_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    _request(backend, 'lib.del', songs=[audio_file])
    assert database.get_song_via_alias('test_alias') is SENTINELS.ALIAS_NOT_FOUND


def test_lib_del_batch_multiple(backend, tmp_path):
    _make_wav(tmp_path / 'a.wav')
    _make_wav(tmp_path / 'b.wav')
    paths = [str(tmp_path / 'a.wav'), str(tmp_path / 'b.wav')]
    _request(backend, 'lib.add', paths=paths)
    response = _request(backend, 'lib.del', songs=paths)
    assert response['code'] == 0
    assert '2/2' in response['msg']
    assert backend.database.song_exists(1) is False
    assert backend.database.song_exists(2) is False


def test_lib_del_batch_partial_failure(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.del', songs=[audio_file, 'ghost_song'])
    assert response['code'] == 0
    assert '1/2' in response['msg']
    assert len(response['failed']) == 1
    assert 'does not exist' in response['failed'][0]['msg']
    assert backend.database.song_exists(1) is False


def test_lib_del_batch_all_failed(backend):
    response = _request(backend, 'lib.del', songs=['ghost_a', 'ghost_b'])
    assert response['code'] == 1
    assert '0/2' in response['msg']
    assert len(response['failed']) == 2


def test_lib_del_batch_empty(backend):
    response = _request(backend, 'lib.del', songs=[])
    assert response['code'] == 1
    assert 'empty list of songs' in response['msg']


def test_lib_alias_bind(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    assert response['code'] == 0
    assert backend.database.get_song_via_alias('favorite') == 1


def test_lib_alias_bind_duplicate(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    response = _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    assert response['code'] == 1
    assert 'already' in response['msg']


def test_lib_alias_bind_missing_song(backend):
    response = _request(backend, 'lib.alias.bind', song='ghost_song', alias='favorite')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_alias_list(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    _request(backend, 'lib.alias.bind', song=audio_file, alias='workout')
    response = _request(backend, 'lib.alias.list', song=audio_file)
    assert response['code'] == 0
    assert response['attachment'] == ['test_audio', 'favorite', 'workout']


def test_lib_alias_list_missing_song(backend):
    response = _request(backend, 'lib.alias.list', song='ghost_song')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_alias_del(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    response = _request(backend, 'lib.alias.unbind', alias='favorite')
    assert response['code'] == 0
    assert backend.database.get_song_via_alias('favorite') is SENTINELS.ALIAS_NOT_FOUND


def test_lib_alias_del_keeps_song(backend, audio_file):
    """Deleting an alias must not delete the song it was bound to."""
    _request(backend, 'lib.add', paths=[audio_file])
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


def test_replay_before_open(backend):
    response = _request(backend, 'replay')
    assert response['code'] == 1
    assert 'neither playing nor paused' in response['msg']


def test_replay_after_open(backend, audio_file):
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    response = _request(backend, 'replay')
    assert response['code'] == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == audio_file


def test_replay_clears_memorized_pos(backend, audio_file):
    database = backend.database
    response = _request(backend, 'open', song=audio_file)
    assert response['code'] == 0
    database.set_pos(audio_file, 1000)
    assert database.get_pos(audio_file) == 1000

    response = _request(backend, 'replay')
    assert response['code'] == 0
    assert database.get_pos(audio_file) is SENTINELS.POS_NOT_FOUND


def test_search_missing_keyword(backend):
    response = _request(backend, 'lib.search')
    assert response['code'] == 1
    assert 'keyword' in response['msg']


def test_search_no_results(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.search', keyword=['nonexistent'])
    assert response['code'] == 0
    assert response['attachment'] == []


def test_search_by_name(backend, audio_file):
    database = backend.database
    _request(backend, 'lib.add', paths=[audio_file])
    song_id = database.get_all_song_info()[0]['id']
    database.set_song_meta(song_id, 'name', 'My Awesome Song')
    response = _request(backend, 'lib.search', keyword=['awesome'])
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['name'] == 'My Awesome Song'


def test_search_by_alias(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file], aliases=['MyAlias'])
    response = _request(backend, 'lib.search', keyword=['alias'])
    assert response['code'] == 0
    assert len(response['attachment']) == 1


def test_search_case_insensitive(backend, audio_file):
    database = backend.database
    _request(backend, 'lib.add', paths=[audio_file])
    song_id = database.get_all_song_info()[0]['id']
    database.set_song_meta(song_id, 'artist', 'Metallica')
    response = _request(backend, 'lib.search', keyword=['METALLICA'])
    assert response['code'] == 0
    assert len(response['attachment']) == 1


def test_search_partial_match(backend, audio_file):
    database = backend.database
    _request(backend, 'lib.add', paths=[audio_file])
    song_id = database.get_all_song_info()[0]['id']
    database.set_song_meta(song_id, 'name', 'Hello World')
    response = _request(backend, 'lib.search', keyword=['wor'])
    assert response['code'] == 0
    assert len(response['attachment']) == 1


def test_search_multi_keyword_and(backend, audio_file):
    database = backend.database
    _request(backend, 'lib.add', paths=[audio_file])
    song_id = database.get_all_song_info()[0]['id']
    database.set_song_meta(song_id, 'name', 'My Awesome Song')
    database.set_song_meta(song_id, 'artist', 'Metallica')

    # AND(默认):两个 keyword 都命中 → 匹配
    response = _request(backend, 'lib.search', keyword=['awesome', 'metallica'])
    assert response['code'] == 0
    assert len(response['attachment']) == 1

    # AND:一个不命中 → 不匹配
    response = _request(backend, 'lib.search', keyword=['awesome', 'ghost'])
    assert response['code'] == 0
    assert response['attachment'] == []


def test_search_multi_keyword_or(backend, audio_file):
    database = backend.database
    _request(backend, 'lib.add', paths=[audio_file])
    song_id = database.get_all_song_info()[0]['id']
    database.set_song_meta(song_id, 'name', 'My Awesome Song')

    # OR:任一 keyword 命中 → 匹配
    response = _request(backend, 'lib.search', keyword=['awesome', 'ghost'], **{'or': True})
    assert response['code'] == 0
    assert len(response['attachment']) == 1

    # OR:全不命中 → 不匹配
    response = _request(backend, 'lib.search', keyword=['ghost1', 'ghost2'], **{'or': True})
    assert response['code'] == 0
    assert response['attachment'] == []



def test_jump_missing_progress(backend):
    response = _request(backend, 'jump')
    assert response['code'] == 1
    assert 'progress' in response['msg']


def test_jump_before_open(backend):
    response = _request(backend, 'jump', progress=50)
    assert response['code'] == 1
    assert 'neither playing nor paused' in response['msg']


def test_jump_lower_than_zero(backend):
    response = _request(backend, 'jump', progress=-1)
    assert response['code'] == 1
    assert 'lower than 0' in response['msg']


def test_jump_higher_than_100(backend):
    response = _request(backend, 'jump', progress=101)
    assert response['code'] == 1
    assert 'higher than 100' in response['msg']


def test_jump_success(backend, audio_file):
    _request(backend, 'open', song=audio_file)
    response = _request(backend, 'jump', progress=50)
    assert response['code'] == 0
    assert 'jumped to' in response['msg']
    status = _request(backend, 'status')
    assert status['attachment']['time'] >= 1500


def test_jump_ended_state_not_crash(backend, monkeypatch):
    """Ended/Stopped state with a known length must return a proper error, not dispatch_failed."""
    monkeypatch.setattr(backend.player, 'get_progress', lambda: {'length': 3000, 'time': 3000})
    response = _request(backend, 'jump', progress=50)
    assert response['code'] == 1
    assert 'neither playing nor paused' in response['msg']


def test_seek_missing_time(backend):
    response = _request(backend, 'seek')
    assert response['code'] == 1
    assert 'time' in response['msg']


def test_seek_invalid_time(backend):
    response = _request(backend, 'seek', time='abc')
    assert response['code'] == 1
    assert 'invalid time' in response['msg']


def test_seek_invalid_time_negative(backend):
    response = _request(backend, 'seek', time='-5:30')
    assert response['code'] == 1
    assert 'invalid time' in response['msg']


def test_seek_invalid_time_too_many_parts(backend):
    response = _request(backend, 'seek', time='1:2:3:4')
    assert response['code'] == 1
    assert 'invalid time' in response['msg']


def test_seek_before_open(backend):
    response = _request(backend, 'seek', time='1')
    assert response['code'] == 1
    assert 'neither playing nor paused' in response['msg']


def test_seek_success(backend, audio_file):
    _request(backend, 'open', song=audio_file)
    response = _request(backend, 'seek', time='00:01')
    assert response['code'] == 0
    assert 'jumped to' in response['msg']
    status = _request(backend, 'status')
    assert status['attachment']['time'] >= 500


def test_seek_pos_too_late(backend, audio_file):
    _request(backend, 'open', song=audio_file)
    response = _request(backend, 'seek', time='1:00')
    assert response['code'] == 1
    assert 'later than the end' in response['msg']


def test_seek_hours_parsed_correctly(backend):
    """1:02:03 must resolve to 1h2m3s (the 3600000 fix), verified without a player."""
    from src.utils import parse_time, format_time
    assert format_time(parse_time('1:02:03')) == '01:02:03'


def test_scan_missing_dir(backend):
    response = _request(backend, 'lib.scan')
    assert response['code'] == 1
    assert 'dir' in response['msg']


def test_scan_invalid_directory(backend, tmp_path):
    response = _request(backend, 'lib.scan', dir=str(tmp_path / 'not_a_dir'))
    assert response['code'] == 1
    assert 'not a valid directory' in response['msg']


def test_scan_dry_run(backend, tmp_path):
    _make_wav(tmp_path / 'test_a.wav')
    _make_wav(tmp_path / 'test_b.wav')
    response = _request(backend, 'lib.scan', dir=str(tmp_path), dry_run=True)
    assert response['code'] == 0
    assert len(response['attachment']) == 2
    assert response['attachment'][0].endswith('test_a.wav')
    # dry run must not add anything to the library
    assert _request(backend, 'lib.list')['attachment'] == []


def test_scan_success(backend, tmp_path):
    _make_wav(tmp_path / 'test_a.wav')
    _make_wav(tmp_path / 'test_b.wav')
    response = _request(backend, 'lib.scan', dir=str(tmp_path))
    assert response['code'] == 0
    assert '2/2' in response['msg']
    assert response['failed'] == []
    assert len(_request(backend, 'lib.list')['attachment']) == 2


def test_scan_partial_failure(backend, tmp_path):
    _make_wav(tmp_path / 'test_a.wav')
    _make_wav(tmp_path / 'test_b.wav')
    _request(backend, 'lib.add', paths=[str(tmp_path / 'test_a.wav')])
    response = _request(backend, 'lib.scan', dir=str(tmp_path))
    assert response['code'] == 0
    assert '1/2' in response['msg']
    assert len(response['failed']) == 1
    assert 'already exists' in response['failed'][0]['msg']
    assert len(_request(backend, 'lib.list')['attachment']) == 2


def test_scan_recurse(backend, tmp_path):
    sub = tmp_path / 'sub'
    sub.mkdir()
    _make_wav(sub / 'test_c.wav')
    response = _request(backend, 'lib.scan', dir=str(tmp_path))
    assert response['code'] == 0
    assert 'No supported audio file found' in response['msg']

    response = _request(backend, 'lib.scan', dir=str(tmp_path), recurse=True)
    assert response['code'] == 0
    assert '1/1' in response['msg']
    assert len(_request(backend, 'lib.list')['attachment']) == 1


def test_scan_with_playlist(backend, tmp_path):
    _make_wav(tmp_path / 'test_a.wav')
    database = backend.database
    database.create_playlist('scanlist')
    response = _request(backend, 'lib.scan', dir=str(tmp_path), playlist='scanlist')
    assert response['code'] == 0
    assert 'added 1 song(s) to playlist' in response['msg']
    playlist_id = database.get_playlist_via_name('scanlist')
    assert len(database.get_playlist_songs(playlist_id)) == 1


def test_lib_info_single_song(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    response = _request(backend, 'lib.info', songs=[audio_file])
    assert response['code'] == 0
    assert 'got information of [1/1] songs' in response['msg']
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['id'] == song_id
    assert response['attachment'][0]['path'] == audio_file
    assert response['failed'] == []


def test_lib_info_multiple_songs(backend, audio_file, tmp_path):
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    database = backend.database
    database.add_song(audio_file)
    database.add_song(second)

    response = _request(backend, 'lib.info', songs=[audio_file, second])
    assert response['code'] == 0
    assert 'got information of [2/2] songs' in response['msg']
    assert len(response['attachment']) == 2


def test_lib_info_by_alias(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'my_song')
    response = _request(backend, 'lib.info', songs=['my_song'])
    assert response['code'] == 0
    assert response['attachment'][0]['id'] == song_id


def test_lib_info_partial_failure(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    response = _request(backend, 'lib.info', songs=[audio_file, 'ghost_song'])
    # 至少一个成功 → code 0,失败的进 failed
    assert response['code'] == 0
    assert 'got information of [1/2] songs' in response['msg']
    assert len(response['attachment']) == 1
    assert len(response['failed']) == 1
    assert 'does not exist' in response['failed'][0]['msg']


def test_lib_info_all_failed(backend, audio_file):
    response = _request(backend, 'lib.info', songs=['ghost_a', 'ghost_b'])
    # 全部失败 → code 1
    assert response['code'] == 1
    assert 'got information of [0/2] songs' in response['msg']
    assert response['attachment'] == {}
    assert len(response['failed']) == 2


def test_lib_info_missing_songs_key(backend, audio_file):
    backend.database.add_song(audio_file)
    response = _request(backend, 'lib.info')
    assert response['code'] == 1
    assert 'songs' in response['msg']


def test_lib_info_songs_must_be_list(backend, audio_file):
    backend.database.add_song(audio_file)
    # IterType(str):单字符串不是 list/tuple → InvalidKeyType
    response = _request(backend, 'lib.info', songs=audio_file)
    assert response['code'] == 1
    assert 'must be a list or tuple' in response['msg']


def test_lib_info_songs_element_type(backend, audio_file):
    backend.database.add_song(audio_file)
    # 元素类型不对 → InvalidElementType
    response = _request(backend, 'lib.info', songs=[123])
    assert response['code'] == 1
    assert 'every element' in response['msg']


def test_lib_info_with_aliases(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'my_song')
    response = _request(backend, 'lib.info', songs=[audio_file], show_aliases=True)
    assert response['code'] == 0
    assert response['attachment'][0]['aliases'] == ['my_song']


def test_lib_info_with_playlists(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    playlist_id = database.create_playlist('work')[0]
    database.add_song_to_playlist(playlist_id, song_id)
    response = _request(backend, 'lib.info', songs=[audio_file], show_playlists=True)
    assert response['code'] == 0
    assert response['attachment'][0]['playlists'] == ['work']


def test_lib_prune_dry_run_empty(backend, audio_file):
    _request(backend, 'lib.add', paths=[audio_file])
    response = _request(backend, 'lib.prune', dry_run=True)
    assert response['code'] == 0
    assert response['attachment'] == []


def test_lib_prune_dry_run_finds_missing(backend, tmp_path):
    database = backend.database
    ghost = str(tmp_path / 'ghost.wav')
    database.add_song(ghost)
    response = _request(backend, 'lib.prune', dry_run=True)
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['path'] == ghost
    # dry run must not delete anything
    assert database.song_exists(1)


def test_lib_prune_removes_missing(backend, tmp_path):
    database = backend.database
    ghost = str(tmp_path / 'ghost.wav')
    ghost_id, _ = database.add_song(ghost)
    real = str(tmp_path / 'real.wav')
    _make_wav(real)
    real_id, _ = database.add_song(real)
    response = _request(backend, 'lib.prune')
    assert response['code'] == 0
    assert database.song_exists(ghost_id) is False
    assert database.song_exists(real_id) is True


def test_lib_prune_removes_from_current_playlist(backend, audio_file, tmp_path):
    """A song in the current playlist whose file disappears later must be removed from both DB and playlist."""
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    _open_playlist_with_songs(backend, [audio_file, second], 'pair')
    assert backend.current_song_info is not None
    assert len(backend.current_song_info) == 2

    os.remove(second)  # file goes missing after the playlist was opened
    response = _request(backend, 'lib.prune')
    assert response['code'] == 0
    assert len(backend.database.get_all_song_info()) == 1
    paths = [s['path'] for s in backend.current_song_info]
    assert second not in paths
    assert audio_file in paths


def test_shuffle_toggle_on_off(backend):
    response = _request(backend, 'shuffle')
    assert response['code'] == 0
    assert 'on' in response['msg']
    assert backend.shuffle is True

    response = _request(backend, 'shuffle')
    assert response['code'] == 0
    assert 'off' in response['msg']
    assert backend.shuffle is False


def test_shuffle_next_uses_order_and_reshuffles(backend, audio_file, tmp_path, monkeypatch):
    _, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    backend.shuffle = True
    backend.shuffle_order = [1, 0]  # current (0) sits at the tail: next wraps and reshuffles

    reshuffled = []
    monkeypatch.setattr('src.backend.random.shuffle', lambda lst: reshuffled.append(list(lst)))

    response = _request(backend, 'next')
    assert response['code'] == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second
    assert len(reshuffled) == 1  # tail wrap triggers reshuffle


def test_shuffle_prev_wraps_without_reshuffle(backend, audio_file, tmp_path, monkeypatch):
    first, _ = _open_two_song_playlist(backend, audio_file, tmp_path)
    backend.shuffle = True
    backend.shuffle_order = [1, 0]
    backend.current_song_num = 1  # second song, at position 0 of the order

    reshuffled = []
    monkeypatch.setattr('src.backend.random.shuffle', lambda lst: reshuffled.append(list(lst)))

    response = _request(backend, 'prev')
    assert response['code'] == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == first  # wraps to tail without reshuffle
    assert len(reshuffled) == 0


def test_shuffle_next_without_songs(backend):
    backend.shuffle = True
    response = _request(backend, 'next')
    assert response['code'] == 1
    assert 'no songs are being played' in response['msg']


def test_shuffle_order_rebuilt_on_open(backend, audio_file, tmp_path, monkeypatch):
    backend.shuffle = True
    reshuffled = []
    monkeypatch.setattr('src.backend.random.shuffle', lambda lst: reshuffled.append(list(lst)))
    _open_two_song_playlist(backend, audio_file, tmp_path)
    assert len(backend.shuffle_order) == 2


def test_loop_toggle_on_off(backend):
    response = _request(backend, 'loop')
    assert response['code'] == 0
    assert 'on' in response['msg']
    assert backend.loop is True

    response = _request(backend, 'loop')
    assert response['code'] == 0
    assert 'off' in response['msg']
    assert backend.loop is False


def test_loop_next_on_end_replays_current(backend, audio_file, tmp_path):
    first, _ = _open_two_song_playlist(backend, audio_file, tmp_path)
    backend.loop = True

    response = _request(backend, 'next', on_end=True)
    assert response['code'] == 0
    assert 'replayed' in response['msg']
    assert backend.current_song_num == 0  # stays on the same song
    status = _request(backend, 'status')
    assert status['attachment']['path'] == first


def test_loop_next_on_end_without_loop_advances(backend, audio_file, tmp_path):
    _, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    response = _request(backend, 'next', on_end=True)
    assert response['code'] == 0
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


def test_loop_manual_next_still_advances(backend, audio_file, tmp_path):
    _, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    backend.loop = True

    response = _request(backend, 'next')
    assert response['code'] == 0
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


def test_invalid_key_type(backend):
    response = _request(backend, 'switch', number='abc')
    assert response['code'] == 1
    assert 'must be a integer' in response['msg']


def test_optional_key_none_accepted(backend, audio_file):
    response = _request(backend, 'lib.add', paths=[audio_file])
    assert response['code'] == 0


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
    assert 'no metadata was provided' in response['msg']


def test_lib_meta_set_song_not_in_library(backend):
    response = _request(backend, 'lib.meta.set', song='ghost_song', name='Foo')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']


def test_lib_meta_set_missing_song_key(backend):
    response = _request(backend, 'lib.meta.set', name='Foo')
    assert response['code'] == 1
    assert 'song' in response['msg']


def test_play_all_empty_library(backend):
    response = _request(backend, 'play-all')
    assert response['code'] == 1
    assert 'none in library' in response['msg']


def test_play_all_two_songs(backend, audio_file, tmp_path):
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    backend.database.add_song(audio_file)
    backend.database.add_song(second)

    response = _request(backend, 'play-all')
    assert response['code'] == 0
    assert backend.current_playlist is SENTINELS.PLAY_ALL
    assert backend.current_song_num == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == audio_file


def test_play_all_restores_last_num(backend, audio_file, tmp_path):
    first = audio_file
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    backend.database.add_song(first)
    backend.database.add_song(second)

    _request(backend, 'play-all')
    _request(backend, 'switch', number=2)
    assert backend.current_song_num == 1

    response = _request(backend, 'play-all')
    assert response['code'] == 0
    assert 'last played number detected' in response['msg']
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


def test_play_all_restores_zero_when_never_played(backend, audio_file, tmp_path):
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    backend.database.add_song(audio_file)
    backend.database.add_song(second)

    response = _request(backend, 'play-all')
    assert response['code'] == 0
    # 从未播过 → 从 0 开始,不应有 'last played number detected'
    assert 'last played number detected' not in response['msg']
    assert backend.current_song_num == 0


def test_continue_last_no_last_song(backend):
    response = _request(backend, 'continue_last')
    assert response['code'] == 1
    assert 'No last song' in response['msg']


def test_continue_last_opens_last_song(backend, audio_file):
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.set_setting('last_is_all', '0')
    database.set_setting('last_song', audio_file)
    database.set_setting('last_cwd', os.getcwd())

    response = _request(backend, 'continue_last')
    assert response['code'] == 0
    assert backend.current_song_num == 0
    status = _request(backend, 'status')
    assert status['attachment']['path'] == audio_file


def test_continue_last_play_all_mode(backend, audio_file, tmp_path):
    second = str(tmp_path / 'test_b.wav')
    _make_wav(second)
    backend.database.add_song(audio_file)
    backend.database.add_song(second)

    database = backend.database
    database.set_setting('last_is_all', '1')
    database.set_setting('last_song', audio_file)
    database.set_setting('last_cwd', os.getcwd())

    response = _request(backend, 'continue_last')
    assert response['code'] == 0
    assert backend.current_playlist is SENTINELS.PLAY_ALL


def test_continue_last_ignores_num_setting(backend, audio_file):
    # 旧的全局 last_num setting 不应再影响 continue_last(已被 playlist last_num 取代)
    database = backend.database
    database.add_song(audio_file)
    database.set_setting('last_is_all', '0')
    database.set_setting('last_song', audio_file)
    database.set_setting('last_cwd', os.getcwd())
    database.set_setting('last_num', 999)  # 毒数据:若被读取会导致越界

    response = _request(backend, 'continue_last')
    assert response['code'] == 0
    assert backend.current_song_num == 0


def test_open_playlist_restores_last_num(backend, audio_file, tmp_path):
    first, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    assert backend.current_song_num == 0

    # 切到第二首 → last_num 应写入该 playlist
    _request(backend, 'switch', number=2)
    assert backend.current_song_num == 1
    playlist_id = backend.database.get_playlist_via_name('pair')
    assert backend.database.get_playlist_last_num(playlist_id) == 1

    # 重新打开同一 playlist → 恢复到上次位置
    response = _request(backend, 'open', song='pair')
    assert response['code'] == 0
    assert 'last played number detected' in response['msg']
    assert backend.current_song_num == 1
    status = _request(backend, 'status')
    assert status['attachment']['path'] == second


def test_open_playlist_first_time_starts_at_zero(backend, audio_file, tmp_path):
    first, _ = _open_two_song_playlist(backend, audio_file, tmp_path)
    # 首次打开:last_num 不存在 → 走 else 分支,写 0 并从头播,无恢复消息
    assert backend.current_song_num == 0
    playlist_id = backend.database.get_playlist_via_name('pair')
    assert backend.database.get_playlist_last_num(playlist_id) == 0


def test_switch_saves_playlist_last_num(backend, audio_file, tmp_path):
    first, second = _open_two_song_playlist(backend, audio_file, tmp_path)
    playlist_id = backend.database.get_playlist_via_name('pair')
    assert backend.database.get_playlist_last_num(playlist_id) == 0

    _request(backend, 'switch', number=2)
    assert backend.database.get_playlist_last_num(playlist_id) == 1

    _request(backend, 'switch', number=1)
    assert backend.database.get_playlist_last_num(playlist_id) == 0


def test_set_current_song_does_not_overwrite_last_num(backend, audio_file, tmp_path):
    # _set_current_song 初始化 current_song_num=0 时不应写库(update_database=False)
    first, _ = _open_two_song_playlist(backend, audio_file, tmp_path)
    playlist_id = backend.database.get_playlist_via_name('pair')

    _request(backend, 'switch', number=2)
    assert backend.database.get_playlist_last_num(playlist_id) == 1

    # 打开单曲(不在当前列表)→ _set_current_song 被调用,不应把 playlist 的 last_num 覆盖成 0
    other_file = audio_file.replace('test_audio', 'test_other')
    _request(backend, 'open', song=other_file)
    assert backend.database.get_playlist_last_num(playlist_id) == 1


