import os

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
    response = backend.dispatch({'action': 'status'})
    assert response['code'] == 1
    assert 'cwd' in response['msg']


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
    assert backend.current_song_info['path'] == audio_file


def test_open_alias_priority_over_path(backend, audio_file, tmp_path):
    """Alias lookup must win even if the alias string is not a real path."""
    database = backend.database
    song_id, _ = database.add_song(audio_file)
    database.bind_alias(song_id, 'test_alias')
    response = _request(backend, 'open', song='test_alias')
    assert response['code'] == 0
    assert backend.current_song_info['id'] == song_id


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
    response = _request(backend, 'lib.list')
    assert response['code'] == 0
    assert response['attachment'] == []


def test_lib_list_after_add(backend, audio_file):
    _request(backend, 'lib.add', path=audio_file)
    response = _request(backend, 'lib.list')
    assert response['code'] == 0
    assert len(response['attachment']) == 1
    assert response['attachment'][0]['path'] == audio_file


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
    assert backend.current_song_info == {'path': audio_file}


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
    response = _request(backend, 'lib.alias.del', alias='favorite')
    assert response['code'] == 0
    assert backend.database.get_song_via_alias('favorite') is SENTINELS.ALIAS_NOT_FOUND


def test_lib_alias_del_keeps_song(backend, audio_file):
    """Deleting an alias must not delete the song it was bound to."""
    _request(backend, 'lib.add', path=audio_file)
    _request(backend, 'lib.alias.bind', song=audio_file, alias='favorite')
    _request(backend, 'lib.alias.del', alias='favorite')
    assert backend.database.get_song_via_path(audio_file) == 1


def test_lib_alias_del_not_exist(backend):
    response = _request(backend, 'lib.alias.del', alias='ghost_alias')
    assert response['code'] == 1
    assert 'does not exist' in response['msg']
