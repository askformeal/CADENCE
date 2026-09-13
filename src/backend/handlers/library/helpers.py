from pathlib import Path

import syncedlyrics

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src import gen_response
from src.sentinels import SENTINELS
from src.utils.misc import extract_file_meta, sort_songs, verify_path_format
from src.utils.time_ import format_time

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def get_song(ctx, song, cwd): # try to get song id from database
    id = ctx.database.get_song_via_alias(song)
    if id is not SENTINELS.ALIAS_NOT_FOUND:
        logger.debug(f'Got song ID {id} via alias {song}')
        return id

    elif song.isdecimal() and ctx.database.song_exists(int(song)): # isdecimal rules out floats
        logger.debug(f'Got song ID {int(song)} via song ID') # sure, why not
        return int(song)

    elif cwd is not None:
        path = Path(cwd) / song
        id = ctx.database.get_song_via_path(str(path))
        if id is not SENTINELS.SONG_NOT_FOUND:
            logger.debug(f'Got song ID {id} via path {path}')
            return id
        else:
            return SENTINELS.NOT_IN_LIB
    else:
        return SENTINELS.MISSING_CWD

def get_song_playlist_names(ctx, song_id):
    playlist_ids = ctx.database.get_song_playlists(song_id)
    playlist_info = ctx.database.get_playlists_info(playlist_ids)
    return list(map(lambda pl: pl['name'], playlist_info))

def get_playlist_songs(ctx, name, return_id=False):
    playlist_id = ctx.database.get_playlist_via_name(name)
    if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
        ids = ctx.database.get_playlist_songs(playlist_id)
        if ids is not SENTINELS.PLAYLIST_EMPTY:
            info = ctx.database.get_song_info(ids)
            info = sort_songs(info)
            result = info
        else:
            result = SENTINELS.PLAYLIST_EMPTY
    else:
        result = SENTINELS.PLAYLIST_NOT_FOUND

    if return_id:
        return result, playlist_id
    else:
        return result

def insert_songs_aliases(ctx, info):
    for i, song in enumerate(info):
        aliases = ctx.database.get_song_aliases(song['id'])
        info[i]['aliases'] = aliases
    return info

def insert_songs_playlist_names(ctx, info):
    for i, song in enumerate(info):
        playlists_id = ctx.database.get_song_playlists(song['id'])
        playlists_info = ctx.database.get_playlists_info(playlists_id)
        info[i]['playlists'] = list(map(lambda pl: pl['name'], playlists_info))
    return info

def add_song(ctx, path, set_meta=True, bind_alias=True, set_lyric=True, alias=None, cwd=None, loose_path=False, return_id=False) -> tuple[int, gen_response.Response] | gen_response.Response:
    song_id = None
    if not Path(path).is_absolute():
        if cwd is None:
            response = gen_response.MissingCWD(f'add-path-to-library')
            path = None
        else:
            path = str(Path(cwd) / path)

    if path is not None and (Path(path).is_file() or (loose_path and verify_path_format(path))):
        add_response = None
        alias_response = None
        meta_response = None
        auto_alias_response = None
        song_id, ignored = ctx.database.add_song(path)
        if not ignored:
            add_response = gen_response.Success(f'added song \"{path}\" to library')

            # --- manual alias ---
            if alias is not None:
                result = ctx.database.bind_alias(song_id, alias)
                if result is SENTINELS.ALIAS_EXISTS:
                    alias_msg = f'can not bind alias \"{alias}\" to the song'
                else:
                    alias_msg = f'bound alias \"{alias}\" to the song'
                alias_response = gen_response.Success(alias_msg)

            meta = extract_file_meta(path)

            # --- auto set metadata ---
            if set_meta:
                count = 0
                for tag, value in meta.items():
                    ctx.database.set_song_meta(song_id, tag, value)
                    if value is not None:
                        count += 1
                meta_response = gen_response.Success(f'set {count} metadata of the song from file')
            else:
                duration = meta.get('duration', None)
                bitrate = meta.get('bitrate', None)
                sample_rate = meta.get('sample_rate', None)
                channels = meta.get('channels', None)

                ctx.database.set_song_meta(song_id, 'duration', duration)
                ctx.database.set_song_meta(song_id, 'bitrate', bitrate)
                ctx.database.set_song_meta(song_id, 'sample_rate', sample_rate)
                ctx.database.set_song_meta(song_id, 'channels', channels)

                meta_response = gen_response.Success(f'set duration to {format_time(duration)}, bitrate to {bitrate}, sample rate to {sample_rate} and channels to {channels}')

            # --- auto bind alias ---
            if bind_alias:
                name = meta.get('name', None)
                if name is not None and not ctx.database.alias_exists(name):
                    ctx.database.bind_alias(song_id, name)
                    bind_msg = f'bound alias \"{name}\" from song name in metadata'
                else:
                    logger.info(f'Name metadata of song with id {song_id} and path {path} does not exist or is already used. Now try to use filename instead')
                    name = Path(path).stem
                    result = ctx.database.bind_alias(song_id, name)
                    if result is SENTINELS.ALIAS_EXISTS:
                        logger.info(f'Can not find a suitable alias for song with id {song_id} and path {path}. Auto alias binding canceled')
                        bind_msg = f'can not find and bind an available alias for the song automatically'
                    else:
                        bind_msg = f'bound alias \"{name}\" from filename'
                auto_alias_response = gen_response.Success(bind_msg)

            # --- auto set lyric file ---
            if set_lyric:
                lyric_path = Path(path).with_suffix('.lrc')
                if lyric_path.is_file():
                    ctx.database.set_song_meta(song_id, 'lyric', str(lyric_path))

            response = add_response + alias_response + meta_response + auto_alias_response
        else:
            response = gen_response.Failed(f'can not add \"{path}\" because a song of the same path already exists in library')
    else:
        response = gen_response.InvalidPath(path)

    if return_id:
        return song_id, response
    else:
        return response

def fetch_lyric(song):
    song_id, search_term = song
    lrc = syncedlyrics.search(
        search_term,
        synced_only=True,
    )
    return song_id, lrc