from pathlib import Path

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.constants import SEARCH_META
from src import gen_response
from src.sentinels import SENTINELS
from src.utils import extract_file_meta, format_time, sort_songs, verify_path_format, shallow_scan, recurse_scan

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def info(ctx, request):
    songs = request['songs']
    show_aliases = request['show_aliases']
    show_playlists = request['show_playlists']
    force_id = request['force_id']
    cwd = request.get('cwd', None)
    
    failed = []
    info = []
    
    for song in songs:
        song_id = None
        if force_id:
            if song.isdecimal() and ctx.database.song_exists(int(song)):
                song_id = int(song)
            else:
                failed.append(gen_response.SongNotExist(f'get information of song \"{song}\"'))
        else:
            get_song_result = get_song(ctx, song, cwd)
            if get_song_result is SENTINELS.MISSING_CWD:
                failed.append(gen_response.MissingCWD('lib.info'))
            elif get_song_result is SENTINELS.NOT_IN_LIB:
                failed.append(gen_response.SongNotExist(f'get information of song \"{song}\"'))
            else:
                song_id = get_song_result
        if song_id is not None:
            song_info = ctx.database.get_song_info(song_id)[0]
    
            if show_aliases:
                aliases = ctx.database.get_song_aliases(song_id)
                song_info['aliases'] = aliases
    
            if show_playlists:
                playlist_ids = ctx.database.get_song_playlists(song_id)
                playlist_info = ctx.database.get_playlists_info(playlist_ids)
                playlist_names = list(map(lambda pl: pl['name'], playlist_info))
                song_info['playlists'] = playlist_names
    
            info.append(song_info)
    
    msg = f'got information of [{len(info)}/{len(songs)}] songs'
    if len(info) > 0 or len(songs) == 0:
        return gen_response.Success(msg, attachment=info, failed=failed)
    else:
        return gen_response.Failed(msg, failed=failed)

def list_(ctx, request):
    info = ctx.database.get_all_song_info()
    if request['show_aliases']:
        info = insert_songs_aliases(ctx, info)
    
    if request['show_playlists']:
        info = insert_songs_playlist_names(ctx, info)
    
    return gen_response.Success('obtained information of all songs in library', sort_songs(info))

def search(ctx, request):
    keywords = request['keyword']
    keywords = list(map(lambda k:k.lower(), keywords))
    is_or = request['or']

    results = []

    info = ctx.database.get_all_song_info()
    song_ids = list(map(lambda s: s['id'], info))
    aliases = {}
    if len(song_ids) > 0:
        for song_id, alias in ctx.database.get_multi_song_aliases(song_ids):
            aliases[song_id] = aliases.get(song_id, []) + [alias]

    for song in info:
        song['aliases'] = aliases.get(song['id'], [])

        search_values = []
        for key, value in song.items():
            if key in SEARCH_META and value is not None:
                search_values.append(str(value))

        search_values += song['aliases']

        search_values.append(str(Path(song['path']).stem))

        search_values = list(map(lambda v: v.lower(), search_values))

        matched = dict(zip(keywords, [False] * len(keywords)))

        for keyword in keywords:
            for value in search_values:
                if keyword in value:
                    matched[keyword] = True

        if all(matched.values()) or (True in matched.values() and is_or):
            results.append(song)

    return gen_response.Success(f'{len(results)} result(s) found in library', results)

def add(ctx, request):
    paths = request['paths']
    aliases = request['aliases']
    loose_path = request['loose_path']
    cwd = request.get('cwd', None)
    
    set_meta = not request['skip_meta']
    bind_alias = not request['skip_alias']
    set_lyric = not request['skip_lyric']
    if len(paths) == 0:
        return gen_response.EmptyList('paths')
    elif len(paths) != len(aliases) and len(aliases) > 0:
        return gen_response.Failed('can not add song(s) because the provided number of paths and aliases are not the same')
    else:
        if len(aliases) == 0:
            aliases = [None] * len(paths)
        failed = []
        succeed = [] # otherwise all the info about auto meta and alias will be lost
        for path, alias in zip(paths, aliases):
            add_response = _add_song(ctx, path, set_meta, bind_alias, set_lyric, alias=alias, cwd=cwd, loose_path=loose_path)
            if add_response.ok():
                succeed.append(add_response)
            else:
                failed.append(add_response)
    
        return gen_response.BatchAuto('songs added to library', len(failed), len(paths), attachment=succeed, failed=failed)

def del_(ctx, request):
    songs = request['songs']
    cwd = request.get('cwd', None)

    if len(songs) == 0:
        return gen_response.EmptyList('songs')
    else:
        failed = []

        for song in songs:
            id = get_song(ctx, song, cwd)
            if id is SENTINELS.MISSING_CWD:
                failed.append(gen_response.MissingCWD('lib.del'))
            elif id is SENTINELS.NOT_IN_LIB:
                failed.append(gen_response.SongNotExist(f'delete {song}'))
            else:
                path = ctx.database.get_song_info(id)[0]['path']
                if ctx.playback.current_song_info is not None and ctx.playback.get_playing_info().get('id', None) == id:
                    ctx.playback.current_song_info[ctx.playback.current_song_num] = {'path': path} 
                    ctx.playback.current_song_in_lib = False

                ctx.database.delete_song(id)

        return gen_response.BatchAuto('songs removed from library', len(failed), len(songs), failed=failed)

def prune(ctx, request):
    from ..playback import remove_from_current
    dry_run = request['dry_run']
    info = ctx.database.get_all_song_info()
    found = []
    for song in info:
        if not Path(song['path']).is_file():
            found.append(song)
    if dry_run:
        return gen_response.Success(f'{len(found)} song(s) with unavailable path(s) found in library', attachment=found)
    else:
        failed = []
        for song in found:
            ctx.database.delete_song(song['id'])
            del_response = remove_from_current(ctx, song['path'])

            if not del_response.ok():
                failed.append(del_response)

        return gen_response.Success(f'{len(found)} song(s) with unavailable path(s) found and was removed from library', attachment=found, failed=failed)

def scan(ctx, request):
    missing_cwd = False
    cwd = request.get('cwd', None)
    directory = request['dir']
    if not Path(directory).is_absolute():
        if cwd is None:
            response = gen_response.MissingCWD('lib.scan')
            missing_cwd = True
        else:
            directory = str(Path(cwd) / directory)
    
    if not missing_cwd:
        playlist = request['playlist']
    
        is_recurse = request['recurse']
        dry_run = request['dry_run']
    
        set_meta = not request['skip_meta']
        bind_alias = not request['skip_alias']
        set_lyric = not request['skip_lyric']
    
        failed_responses = []
    
        if Path(directory).is_dir():
            if is_recurse:
                paths = recurse_scan(directory)
            else:
                paths = shallow_scan(directory)
    
            if len(paths) == 0:
                return gen_response.Success(f'No supported audio file found under {directory}', attachment=[])
            else:
                if dry_run:
                    return gen_response.Success(f'{len(paths)} supported audio files found under {directory}', paths)
                else:
                    ids = []
                    for path in paths:
                        song_id, add_response = _add_song(ctx, path, set_meta, bind_alias, set_lyric, return_id=True)
                        if not add_response.ok():
                            failed_responses.append(add_response)
                        else:
                            ids.append(song_id)
    
                    msg = f'added [{len(ids)}/{len(paths)}] file(s) to library'
                    if len(ids) > 0:
                        response = gen_response.Success(msg, failed=failed_responses)
                    else:
                        response = gen_response.Failed(msg, failed=failed_responses)
    
                    if playlist is not None:
                        playlist_id = ctx.database.get_playlist_via_name(playlist)
                        if playlist_id is SENTINELS.PLAYLIST_NOT_FOUND:
                            playlist_msg = f'can not add songs to playlist \"{playlist}\" because it does not exist'
                        else:
                            for song_id in ids:
                                ctx.database.add_song_to_playlist(playlist_id, song_id) # all songs are freshly added, no chance of ignored
    
                            playlist_msg = f'added {len(ids)} song(s) to playlist {playlist}'
                        response += gen_response.Success(playlist_msg)

                    return response
    
        else:
            return gen_response.Failed(f'\"{directory}\" is not a valid directory')

def reset(ctx, request):
    ctx.database.reset()
    if ctx.playback.current_song_in_lib:
        path = ctx.playback.get_playing_info()['path']
        ctx.playback.set_current_song({'path': path}, False)
    return gen_response.Success('database reset')

# ----------------------------------------------------------------------------------------------------------

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

def _add_song(ctx, path, set_meta=True, bind_alias=True, set_lyric=True, alias=None, cwd=None, loose_path=False, return_id=False) -> tuple[int, gen_response.Response] | gen_response.Response:
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