from src.sentinels import SENTINELS


def test_add_song_new(database):
    song_id, ignored = database.add_song(r'C:\music\song.flac')
    assert ignored is False
    assert database.song_exists(song_id)


def test_add_song_duplicate(database):
    first_id, ignored_first = database.add_song(r'C:\music\song.flac')
    second_id, ignored_second = database.add_song(r'C:\music\song.flac')
    assert ignored_first is False
    assert ignored_second is True
    assert first_id == second_id


def test_add_song_path_case_insensitive(database):
    _, ignored_first = database.add_song(r'C:\music\song.FLAC')
    _, ignored_second = database.add_song(r'c:\MUSIC\SONG.flac')
    assert ignored_first is False
    assert ignored_second is True


def test_get_song_via_path(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    assert database.get_song_via_path(r'C:\music\song.flac') == song_id
    assert database.get_song_via_path(r'C:\music\missing.flac') is SENTINELS.SONG_NOT_FOUND


def test_get_song_info(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    second_id, _ = database.add_song(r'C:\music\another.flac')
    info = database.get_song_info(song_id)
    assert info[0]['id'] == song_id
    assert info[0]['path'] == r'C:\music\song.flac'
    assert database.get_song_info(9999) == []
    batch = database.get_song_info([song_id, second_id])
    assert len(batch) == 2


def test_bind_alias(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    assert database.bind_alias(song_id, 'song') is SENTINELS.DONE


def test_bind_alias_duplicate(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    database.bind_alias(song_id, 'song')
    assert database.bind_alias(song_id, 'song') is SENTINELS.ALIAS_EXISTS


def test_bind_alias_to_missing_song(database):
    assert database.bind_alias(9999, 'song') is SENTINELS.SONG_NOT_FOUND


def test_get_song_aliases(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    assert database.get_song_aliases(song_id) == []
    database.bind_alias(song_id, 'song')
    database.bind_alias(song_id, 'other')
    assert database.get_song_aliases(song_id) == ['song', 'other']
    assert database.get_song_aliases(9999) is SENTINELS.SONG_NOT_FOUND


def test_get_song_via_alias(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    database.bind_alias(song_id, 'song')
    assert database.get_song_via_alias('song') == song_id
    assert database.get_song_via_alias('missing') is SENTINELS.ALIAS_NOT_FOUND


def test_delete_alias(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    database.bind_alias(song_id, 'song')
    assert database.unbind_alias('song') is SENTINELS.DONE
    assert database.unbind_alias('song') is SENTINELS.ALIAS_NOT_FOUND


def test_delete_song(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    assert database.delete_song(song_id) is SENTINELS.DONE
    assert database.song_exists(song_id) is False
    assert database.delete_song(song_id) is SENTINELS.SONG_NOT_FOUND


def test_delete_song_cascades_aliases(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    database.bind_alias(song_id, 'song')
    assert database.get_song_via_alias('song') == song_id
    assert database.delete_song(song_id) is SENTINELS.DONE
    assert database.get_song_via_alias('song') is SENTINELS.ALIAS_NOT_FOUND


def test_get_all_song_info_empty(database):
    assert database.get_all_song_info() == []


def test_get_all_song_info_after_add(database):
    database.add_song(r'C:\music\song.flac')
    database.add_song(r'C:\music\other.flac')
    info = database.get_all_song_info()
    assert len(info) == 2
    assert {row['path'] for row in info} == {r'C:\music\song.flac', r'C:\music\other.flac'}


def test_create_playlist(database):
    playlist_id, ignored = database.create_playlist('workout')
    assert ignored is False
    assert database.get_playlist_via_name('workout') == playlist_id


def test_create_playlist_duplicate(database):
    first_id, ignored_first = database.create_playlist('work')
    second_id, ignored_second = database.create_playlist('work')
    assert ignored_first is False
    assert ignored_second is True
    assert first_id == second_id


def test_add_song_to_playlist(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    playlist_id, _ = database.create_playlist('work')
    ignored = database.add_song_to_playlist(playlist_id, song_id)
    assert ignored is False
    assert database.get_playlist_songs(playlist_id) == [song_id]


def test_add_song_to_playlist_duplicate(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    playlist_id, _ = database.create_playlist('work')
    assert database.add_song_to_playlist(playlist_id, song_id) is False
    assert database.add_song_to_playlist(playlist_id, song_id) is True
    assert database.get_playlist_songs(playlist_id) == [song_id]


def test_get_playlist_via_name_missing(database):
    assert database.get_playlist_via_name('ghost') is SENTINELS.PLAYLIST_NOT_FOUND


def test_del_song_from_playlist(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    playlist_id, _ = database.create_playlist('work')
    database.add_song_to_playlist(playlist_id, song_id)
    assert database.del_song_from_playlist(playlist_id, song_id) is SENTINELS.DONE
    assert database.get_playlist_songs(playlist_id) is SENTINELS.PLAYLIST_EMPTY


def test_del_song_from_playlist_song_not_in_playlist(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    other_song_id, _ = database.add_song(r'C:\music\other.flac')
    playlist_id, _ = database.create_playlist('work')
    database.add_song_to_playlist(playlist_id, song_id)
    assert database.del_song_from_playlist(playlist_id, other_song_id) is SENTINELS.PLAYLIST_SONG_NOT_FOUND


def test_del_song_from_playlist_song_not_found(database):
    playlist_id, _ = database.create_playlist('work')
    assert database.del_song_from_playlist(playlist_id, 9999) is SENTINELS.SONG_NOT_FOUND


def test_del_song_from_playlist_playlist_not_found(database):
    song_id, _ = database.add_song(r'C:\music\song.flac')
    assert database.del_song_from_playlist(9999, song_id) is SENTINELS.PLAYLIST_NOT_FOUND
