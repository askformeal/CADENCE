import sys
import os
import logging
from threading import Thread
import random
import socket
import queue
from time import sleep
from pathlib import Path
import vlc
import mutagen

from src import version
from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.constants import DATABASE_PATH, DATABASE_DEV_PATH
from src.constants import HOST, PORT, BACKLOG, ACTION_KEYS, SERVER_TIMEOUT
from src.constants import MAIN_LOOP_INTERVAL, POS_MEMORIZE_INTERVAL, METADATA, FILE_META
from src.constants import PLAY_DEAD_TIME
from src.constants import AUDIO_EXTENSIONS, SOURCES, READABLE_TYPE_NAMES, SEARCH_META
from src.sentinels import SENTINELS
from src.connection import recv_json, send_json
from src.response import gen_response
from src.database import Database
from src.player import Player
from src.utils import format_ms, parse_time

logger = setup_logger(__name__, BACKEND_LOG_PATH)

class Backend:
    def __init__(self):
        self.dev = {'0': False, '1': True}.get(os.environ.get('CADENCE_DEV', '0'), False)

        if self.dev:
            logger.info('DEVELOPMENT MODE ON')
            database_path = DATABASE_DEV_PATH
        else:
            database_path = DATABASE_PATH

        self.exit_code = 0
        self.running = True
        self.dying = False

        self.loop = False

        self.shuffle = False
        self.shuffle_order = []

        self.current_song_info = None
        self.current_song_num = None
        self.current_song_in_lib = False # Use this to prevent KeyError
        self.dispatch_buffer = queue.Queue() # single way
        try:
            self.database = Database(database_path)
        except RuntimeError as e:
            logger.critical(e)
            self.running = False
        else:
            self.player = Player(self.buffer_request)
            logger.debug(f'{__name__} initiated')

    def run(self):
        if self.running:
            logger.info(f'Command-line Audio Decoding Engine with Navigation and Continuous Execution {version} started')

            Thread(target=self._listen, daemon=True).start()
            Thread(target=self._memorize_pos, daemon=True).start()
            self._flush_thread = Thread(target=self._flush_buffer, daemon=True)
            self._flush_thread.start()

            try:
                while self.running:
                    sleep(MAIN_LOOP_INTERVAL)
            except KeyboardInterrupt: # I know this suppose to run in background, but it's useful in developing
                ...

            logger.info('Exit')
            self.dispatch_buffer.put((SENTINELS.EXIT_FLUSHING, SENTINELS.EXIT_FLUSHING))
            self._flush_thread.join()
            self.database.on_exit()
            self.player.on_exit()
            logging.shutdown()
            sys.exit(self.exit_code)

        else:
            sys.exit(1)

    def buffer_request(self, request, connection=None, address=None):            
        if self.dying:
            if connection is not None:
                send_json(connection, gen_response.dying())
        
        elif request.get('action', None) == 'heartbeat':
            if connection is not None:
                send_json(connection, gen_response.success('alive'))
        else:
            source_code = request.get('source', SENTINELS.SOURCE_NOT_PROVIDED)
            source = SOURCES.get(source_code, f'unrecognized source \"{source_code}\"')
            msg = f'Received request: {request} from {source}'
            if connection is not None:
                msg += f' via socket connection from {address}'
            logger.info(msg)
            self.dispatch_buffer.put((request, connection))

    def _flush_buffer(self):
        while self.running:
            request, connection = self.dispatch_buffer.get()
            if request is SENTINELS.EXIT_FLUSHING:
                break
            try:
                response = self.dispatch(request)
            except Exception as e:
                logger.exception(f'Failed to dispatch request:')
                response = gen_response.failed(f'failed to dispatch request: \"{e}\"')

            if self.dev:
                response['msg'] = ' '.join(('[DEV]', response.get('msg','')))
            
            if connection is not None:
                logger.info(f'Send response: {response}')
                send_json(connection, response)
                connection.close()

    def dispatch(self, request):
        logger.debug(f'Dispatch request: {request}')
        response = {}
        action = request.get('action', None)
        cwd = request.get('cwd', None)
        if action is not None:
            keys = ACTION_KEYS.get(action, {})
            for key, info in keys.items():
                key_type, is_required = info
                value = request.get(key, SENTINELS.KEY_NOT_PROVIDED)
                if value is SENTINELS.KEY_NOT_PROVIDED:
                    if is_required:
                        response = self._missing_key(action, key)
                        break
                elif not isinstance(value, key_type) and not (value is None and not is_required): # None type acceptable for non-required keys even if not stated in ACTION_KEYS
                    response = gen_response.invalid_key_type(action, key, READABLE_TYPE_NAMES[key_type])
                    break
            else:

                # ----------------------------------------------------------------

                if action == 'test_alive':
                    return gen_response.success('CADENCE backend is running')

                elif action == 'status':
                    player_status = {
                        vlc.State.Playing: 'playing',
                        vlc.State.Paused: 'paused',
                        vlc.State.Stopped: 'stopped'
                    }.get(self.player.player.get_state(), '[unknown]')

                    if self.current_song_info is None:
                        info = {}
                    else:
                        info = self.current_song_info[self.current_song_num]

                    status = {
                        'path': info.get('path', '[path unknown]'),
                        'name': info.get('name', '[name unknown]'),
                        'artist': info.get('artist', '[artist unknown]'),
                        'album': info.get('album', '[album unknown]'),
                        'in_library': self.current_song_in_lib,
                        'player_status': player_status,
                        'volume': self.player.volume,
                        'mute': self.player.mute
                    }
                    progress = self.player.get_progress()
                    status['length'] = progress['length']
                    status['time'] = progress['time']
                    status['dev'] = self.dev
                    response = gen_response.success('status obtained', status)
                    
                elif action == 'open':
                    paths_to_load = None
                    song = request['song']
                    id = self._get_song(song, cwd)
                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('open', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        self._set_current_song(self.database.get_song_info(id))
                        paths_to_load = self.current_song_info[0]['path']
                    else:
                        path = Path(cwd) / song
                        info = self._get_playlist_songs(song)
                        if info is SENTINELS.PLAYLIST_EMPTY:
                            response = gen_response.failed(f'can not open playlist \"{song}\" because it is empty')

                        elif info is not SENTINELS.PLAYLIST_NOT_FOUND:
                            self._set_current_song(info)
                            paths_to_load = list(map(lambda i: i['path'], info))

                        else:
                            # Not in library, try to open as path
                            if path.is_file():
                                self._set_current_song([{'path': str(path)}], False)
                                paths_to_load = str(path)
                            else:
                                logger.warning(f'Can not open {path}')
                                response = gen_response.invalid_path(str(path))

                    if paths_to_load is not None:
                        response = self._load_paths(paths_to_load, song)

                elif action == 'play-all':
                    info = self.database.get_all_song_info()
                    if len(info) > 0:
                        self._set_current_song(info, True)
                        paths = list(map(lambda x: x['path'], info))
                        response = self._load_paths(paths, 'all-songs')
                    else:
                        response = gen_response.failed('can not open all songs because there is none in library')

                elif action == 'stop':
                    response = self._stop_player()

                elif action == 'pause':
                    result = self.player.pause()
                    response = {
                        SENTINELS.SUCCESS: gen_response.success('player paused'),
                        SENTINELS.INVALID_PLAYER_STATE: gen_response.failed('can not pause player because player is not playing'),
                        SENTINELS.VLC_ERROR: gen_response.vlc_error('pause player'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('pause player')
                    }[result]

                elif action == 'resume':
                    result = self.player.resume()
                    response = {
                        SENTINELS.SUCCESS: gen_response.success('player resumed'),
                        SENTINELS.INVALID_PLAYER_STATE: gen_response.failed('can not resume player because player is not paused'),
                        SENTINELS.VLC_ERROR: gen_response.vlc_error('resume player'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('resume player')
                    }[result]

                elif action == 'toggle':
                    result = self.player.toggle()
                    response = {
                        SENTINELS.SUCCESS: gen_response.success('player toggled'),
                        SENTINELS.INVALID_PLAYER_STATE: gen_response.not_playing_paused('toggle player'),
                        SENTINELS.VLC_ERROR: gen_response.vlc_error('toggle player'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('toggle player')
                    }[result]

                elif action == 'list':
                    response = gen_response.success('obtained current playlist')
                    if self.current_song_info is not None:
                        response['attachment'] = self.current_song_info.copy()
                    else:
                        response['attachment'] = []

                elif action == 'shuffle':
                    self._toggle_shuffle()
                    mode = {True: 'on', False: 'off'}[self.shuffle]
                    response = gen_response.success(f"shuffle mode turned {mode}")

                elif action == 'loop':
                    self.loop = not self.loop
                    mode = {True: 'on', False: 'off'}[self.loop]
                    response = gen_response.success(f'loop mode turned {mode}')

                elif action == 'dice':
                    if self.current_song_info is None:
                        response = gen_response.player_empty('switch to a random song in current playlist')
                    elif len(self.current_song_info) == 1:
                        response = gen_response.failed('can not switch to a random song because there is only one song in current playlist ')
                    else:
                        pool = list(range(len(self.current_song_info)))
                        pool.remove(self.current_song_num)
                        num = random.choice(pool)
                        result = self.player.load_number(num)
                        response = {
                            SENTINELS.SUCCESS: gen_response.success(f'diced to the {num+1}nd song in current playlist'),
                            SENTINELS.PLAYER_EMPTY: gen_response.player_empty(f'switch to the {num+1}nd song in current playlist'),
                            SENTINELS.VLC_ERROR: gen_response.vlc_error(f'switch to the {num+1}nd song in current playlist'),
                            SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout(f'switch to the {num+1}nd song in current playlist'),
                        }[result]
                        self.current_song_num = self.player.number

                elif action == 'switch':
                    num = request['number']
                    if num == 0:
                        response = self._switch_song(0)
                    elif num < 0:
                        response = self._switch_song(num)
                    else:
                        response = self._switch_song(num-1)

                elif action == 'prev':
                    if self.shuffle:
                        result = self.player.load_number(self._switch_shuffle(-1))
                    else:
                        result = self.player.switch_prev()
                    response = {
                        SENTINELS.SUCCESS: gen_response.success('switched to previous song'),
                        SENTINELS.PLAYER_EMPTY: gen_response.player_empty('switch to previous song'),
                        SENTINELS.VLC_ERROR: gen_response.vlc_error('switch to previous song'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('switch to previous song')
                    }[result]
                    self.current_song_num = self.player.number
                    if result is SENTINELS.SUCCESS:
                        response = gen_response.merge(response, self._replay())

                elif action == 'next':
                    on_end = request.get('on_end', False)
                    if on_end:
                        self._del_current_pos()

                    if on_end and self.loop:
                        result = self.player.load_number(self.player.number)
                        response = {
                            SENTINELS.SUCCESS: gen_response.success('replayed current song'),
                            SENTINELS.VLC_ERROR: gen_response.vlc_error('replayed current song'),
                            SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('replayed current song'),
                        }[result]
                    else:
                        if self.shuffle:
                            result = self.player.load_number(self._switch_shuffle(1))
                        else:
                            result = self.player.switch_next()
                        response = {
                            SENTINELS.SUCCESS: gen_response.success('switched to next song'),
                            SENTINELS.PLAYER_EMPTY: gen_response.player_empty('switch to next song'),
                            SENTINELS.VLC_ERROR: gen_response.vlc_error('switch to next song'),
                            SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('switch to next song')
                        }[result]
                        self.current_song_num = self.player.number
                        if result is SENTINELS.SUCCESS:
                            response = gen_response.merge(response, self._replay())

                elif action == 'seek':
                    time = request['time']
                    pos = parse_time(time)
                    if pos is SENTINELS.INVALID_TIME:
                        response = gen_response.failed(f'invalid time: {time}')
                    else:
                        response = self._jump_to_pos(pos)

                elif action == 'jump':
                    percent = request['progress']
                    if percent < 0:
                        response = gen_response.percentage_too_low(percent)
                    elif percent > 100:
                        response = gen_response.percentage_too_high(percent)
                    else:
                        length = self.player.get_progress()['length']
                        if length == -1:
                            response = gen_response.not_playing_paused('jump to progress')
                        else:
                            pos = length * (percent / 100)
                            response = self._jump_to_pos(pos)
                elif action == 'replay':
                    response = self._replay()
                    if response['code'] == 0:
                        self._del_current_pos()

                elif action == 'volume':
                    volume = request['volume']
                    if volume < 0:
                        response = gen_response.percentage_too_low(volume)
                    elif volume > 100:
                        response = gen_response.percentage_too_high(volume)
                    else:
                        self.player.set_volume(volume)
                        response = gen_response.success(f'set volume to {self.player.volume}%')

                elif action == 'mute':
                    self.player.set_mute(not self.player.mute)
                    mode = {True: 'on', False: 'off'}[self.player.mute]
                    response = gen_response.success(f'turned mute mode {mode}')

                elif action == 'lib.search':
                    keyword = request['keyword'].lower()
                    results = []

                    info = self.database.get_all_song_info()
                    for song in info:
                        aliases = self.database.get_song_aliases(song['id'])
                        song['aliases'] = aliases

                        for key, value in song.items():
                            if key in SEARCH_META and keyword in str(value).lower():
                                results.append(song)
                                break
                        else:
                            for alias in aliases:
                                if keyword in alias.lower():
                                    results.append(song)
                                    break

                    response = gen_response.success(f'{len(results)} result(s) found in library', results)

                elif action == 'lib.list':
                    info = self.database.get_all_song_info()
                    if request.get('show_aliases', False):
                        for song in info:
                            aliases = self.database.get_song_aliases(song['id'])
                            song['aliases'] = aliases

                    if request.get('show_playlists', False):
                        for song in info:
                            playlists_id = self.database.get_song_playlists(song['id'])
                            playlists_info = self.database.get_playlists_info(playlists_id)
                            song['playlists'] = list(map(lambda pl: pl['name'], playlists_info))

                    response = gen_response.success('obtained information of all songs in library', self.sort_songs(info))

                elif action == 'lib.add':
                    alias = request.get('alias', None)
                    set_meta = not request.get('skip_meta', False)
                    bind_alias = not request.get('skip_alias', False)
                    response = self._add_song(request['path'], set_meta, bind_alias, alias)

                elif action == 'lib.del':
                    song = request['song']
                    id = self._get_song(song, cwd)
                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('lib.del', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        path = self.database.get_song_info(id)[0]['path']
                        if self.current_song_info is not None and self.current_song_info[self.current_song_num].get('id', None) == id:
                            self.current_song_info[self.current_song_num] = {'path': path} 
                            self.current_song_in_lib = False
                        self.database.delete_song(id)
                        response = gen_response.success(f'deleted song \"{song}\" from library')
                    else:
                        response = gen_response.song_not_exist(f'delete {song}')

                elif action == 'lib.prune':
                    dry_run = request.get('dry_run', False)
                    info = self.database.get_all_song_info()
                    found = []
                    for song in info:
                        if not Path(song['path']).is_file():
                            found.append(song)
                    if dry_run:
                        response = gen_response.success(f'{len(found)} song(s) with unavailable path(s) found in library', attachment=found)
                    else:
                        failed = []
                        for song in found:
                            self.database.delete_song(song['id'])
                            del_response = self._remove_from_current(song['path'])
                            if del_response['code'] != 0:
                                failed.append(del_response)
                        
                        response = gen_response.success(f'{len(found)} song(s) with unavailable path(s) found and was removed from library', attachment=found, failed=failed)

                elif action == 'lib.scan':
                    missing_cwd = False
                    directory = request['dir']
                    if not Path(directory).is_absolute():
                        if cwd is None:
                            response = self._missing_key('lib.scan', 'cwd')
                            missing_cwd = True
                        else:
                            directory = str(Path(cwd) / directory)
                            
                    if not missing_cwd:
                        playlist = request.get('playlist', None)

                        is_recurse = request.get('recurse', False)
                        dry_run = request.get('dry_run', False)

                        set_meta = not request.get('skip_meta', False)
                        bind_alias = not request.get('skip_alias', False)

                        failed_responses = []

                        if Path(directory).is_dir():
                            if is_recurse:
                                paths = self._recurse_scan(directory)
                            else:
                                paths = self._scan(directory)
                            if dry_run:
                                response = gen_response.success(f'{len(paths)} supported audio files found under {directory}', paths)
                            else:
                                ids = []
                                for path in paths:
                                    song_id, add_response = self._add_song(path, set_meta, bind_alias, return_id=True)
                                    if add_response['code'] != 0:
                                        failed_responses.append(add_response)
                                    else:
                                        ids.append(song_id)

                                response = gen_response.success(f'successfully added [{len(ids)}/{len(paths)}] file(s) to library', failed=failed_responses)

                                if playlist is not None:
                                    playlist_id = self.database.get_playlist_via_name(playlist)
                                    if playlist_id is SENTINELS.PLAYLIST_NOT_FOUND:
                                        playlist_msg = f'can not add songs to playlist \"{playlist}\" because it does not exist'
                                    else:
                                        for song_id in ids:
                                            self.database.add_song_to_playlist(playlist_id, song_id) # all songs are freshly added, no chance of ignored

                                        playlist_msg = f'added {len(ids)} song(s) to playlist {playlist}'
                                    response = gen_response.merge(response, gen_response.success(playlist_msg), failed=failed_responses)

                        else:
                            response = gen_response.failed(f'\"{directory}\" is not a valid directory')

                elif action == 'lib.reset':
                    self.database.reset()
                    if self.current_song_in_lib:
                        path = self.current_song_info[self.current_song_num]['path']
                        self._set_current_song({'path': path}, False)
                    response = gen_response.success('database reset')

                elif action == 'lib.meta.set':
                    song_id = self._get_song(request['song'], cwd)
                    if song_id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('lib.meta.set', 'cwd')
                    elif song_id is SENTINELS.NOT_IN_LIB:
                        response = gen_response.song_not_exist(f"set metadata of \"{request['song']}\"")
                    else:
                        metadata = {}
                        for label in METADATA:
                            metadata[label] = request.get(label, None)

                        if True in map(lambda x: x is not None, metadata.values()): # not all meta is none
                            for label, value in metadata.items():
                                if value is not None:
                                    if value == '':
                                        value = SENTINELS.CLEAR_META
                                    self.database.set_song_meta(song_id, label, value)

                            response = gen_response.success('metadata set')

                        else:
                            response = gen_response.failed(f'can not set metadata because no metadata was given')

                elif action == 'lib.alias.list':
                    song = request['song']
                    id = self._get_song(song, cwd)
                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('lib.alias.list', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        aliases = self.database.get_song_aliases(id)
                        response = gen_response.success('obtained all aliases in library', aliases)
                    else:
                        response = gen_response.song_not_exist(f'show aliases of {song}')

                elif action == 'lib.alias.bind':
                    song = request['song']
                    id = self._get_song(song, cwd)

                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('lib.alias.bind', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        result = self.database.bind_alias(id, request['alias'])
                        response = {
                            SENTINELS.ALIAS_EXISTS: gen_response.failed(f'can not bind alias \"{request['alias']}\" because it is already bound to another song in library'),
                            SENTINELS.SUCCESS: gen_response.success(f"bound alias \"{request['alias']}\" to song \"{song}\""),
                            SENTINELS.SONG_NOT_FOUND: gen_response.song_not_exist(f'bind alias to {song}') # not really necessary, but Monica insists
                        }[result]
                    else:
                        response = gen_response.song_not_exist(f'bind alias to {song}')

                elif action == 'lib.alias.unbind':
                    result = self.database.unbind_alias(request['alias'])
                    if result is not SENTINELS.ALIAS_NOT_FOUND:
                        response = gen_response.success(f"unbound alias \"{request["alias"]}\"")
                    else:
                        response = gen_response.failed(f'can not unbind {request["alias"]} because it does not exist in library')

                elif action == 'lib.playlist.list':
                    response = gen_response.success('obtained list of playlist in library')

                    playlist = request.get('playlist', None)
                    if playlist is not None:
                        info = self._get_playlist_songs(playlist)
                        if info is SENTINELS.PLAYLIST_NOT_FOUND:
                            response = gen_response.playlist_not_exist(f'list songs of playlist \"{playlist}\"')
                        elif info is SENTINELS.PLAYLIST_EMPTY:
                            response['attachment'] = []
                        else:
                            response['attachment'] = info
                            
                    else:
                        playlists = self.database.get_all_playlists()
                        response['attachment'] = playlists

                elif action == 'lib.playlist.create':
                    name = request['name']
                    ignored = self.database.create_playlist(name)[1]
                    if not ignored:
                        response = gen_response.success(f'created playlist \"{name}\"')
                    else:
                        response = gen_response.failed(f'can not create \"{name}\" because a playlist of the same name already exists in library')

                elif action == 'lib.playlist.add':
                    playlist = self.database.get_playlist_via_name(request['playlist'])
                    if playlist is not SENTINELS.PLAYLIST_NOT_FOUND:
                        song = self._get_song(request['song'], cwd)
                        if song is SENTINELS.MISSING_CWD:
                            response = gen_response.missing_key('lib.playlist.add', 'cwd')
                        elif song is SENTINELS.NOT_IN_LIB:
                            response = gen_response.song_not_exist(f'add song \"{request['song']}\" to playlist \"{request['playlist']}\"')
                        else:
                            ignored = self.database.add_song_to_playlist(playlist, song)
                            if not ignored:
                                response = gen_response.success(f"added song \"{request['song']}\" to playlist \"{request['playlist']}\"")
                            else:
                                response = gen_response.failed(f'can not add song \"{request['song']}\" to playlist \"{request['playlist']}\" because it is already in the playlist')
                    else:
                        response = gen_response.playlist_not_exist(f'add song to playlist \"{request['playlist']}\"')

                elif action == 'lib.playlist.kick':
                    playlist_id = self.database.get_playlist_via_name(request['playlist'])
                    if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
                        song_id = self._get_song(request['song'], cwd)
                        if song_id is SENTINELS.MISSING_CWD:
                            response = gen_response.missing_key('lib.playlist.kick', 'cwd')
                        elif song_id is SENTINELS.NOT_IN_LIB:
                            response = gen_response.song_not_exist(f'remove song \"{request['song']}\" from playlist \"{request['playlist']}\"')
                        else:
                            result = self.database.del_song_from_playlist(playlist_id, song_id)
                            if result is SENTINELS.PLAYLIST_SONG_NOT_FOUND:
                                response = gen_response.failed(f"can not remove song \"{request['song']}\" from playlist \"{request['playlist']}\" because the song is not in the playlist")
                            else:
                                response = gen_response.success(f"removed song \"{request['song']}\" from playlist \"{request['playlist']}\"")
                    else:
                        response = gen_response.playlist_not_exist(f"remove song {request['song']} from playlist {request['playlist']}")

                elif action == 'lib.playlist.del':
                    playlist_id = self.database.get_playlist_via_name(request['playlist'])
                    if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
                        self.database.del_playlist(playlist_id)
                        response = gen_response.success(f"deleted playlist \"{request['playlist']}\"")
                    else:
                        response = gen_response.playlist_not_exist(f"delete playlist \"{request['playlist']}\"")

                elif action == 'exit':
                    self.exit()
                    response = gen_response.success('CADENCE backend is now exiting')
                else:
                    logger.error(f'Invalid \"action\" value received: {action}')
                    response = gen_response.INVALID_ACTION
        else:
            logger.error('Not \"action\" key found in request')
            response =  gen_response.missing_key('all', 'action')


        return response

    def _load_paths(self, paths, song, jump_to_mem=True):
        result = self.player.load_paths(paths)
        response = {
            SENTINELS.SUCCESS: gen_response.success(f'opened song/playlist \"{song}\"'),
            SENTINELS.PLAYER_LOAD_EMPTY: gen_response.failed('can not load empty list of songs'),
            SENTINELS.VLC_ERROR: gen_response.vlc_error('load path(s)'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('load path(s)'),
        }[result]
        if jump_to_mem and result is SENTINELS.SUCCESS:
            response = gen_response.merge(response, self._jump_to_memorized_pos())
        return response

    def _stop_player(self):
        result = self.player.stop()
        return {
            SENTINELS.SUCCESS: gen_response.success('player stopped'),
            SENTINELS.VLC_ERROR: gen_response.vlc_error('stop player'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout('stop player')
        }[result]

    def _remove_from_current(self, path):        
        if self.current_song_info is not None:
            paths = list(map(lambda s: s['path'], self.current_song_info))
            if path in paths:
                removed_num = paths.index(path)
                paths.remove(path)
                self.current_song_info = self.current_song_info[:removed_num] + self.current_song_info[removed_num+1:]
                if len(paths) > 0:
                    num = self.current_song_num
                    if removed_num < num: # removed before current
                        num -= 1
                    elif removed_num == num:
                        if num >= len(paths):
                            num = len(paths) - 1

                    response = self._load_paths(paths, 'reload current playlist due to deleted song', jump_to_mem=False)
                    response = gen_response.merge(response, self._switch_song(num))
                    return response
                else:
                    self.current_song_info = None
                    self.current_song_num = None
                    self.current_song_in_lib = False
                    return self._stop_player()
            else:
                return gen_response.success('path not in current playlist') # not that anyone will actually read this but, you know, for good measure
        else:
            return gen_response.success('current playlist empty') # same as above

    def _switch_song(self, num):
        max_num = len(self.player.medias)
        if num >= max_num:
            num_to_load = max_num - 1 # 9999999999 will switch the last song
        elif num < 0:
            num_to_load = max(max_num + num, 0) # -3 will switch the third from last song, -9999999999 will switch to the first song
        else:
            num_to_load = num
        result = self.player.load_number(num_to_load)
        response = {
            SENTINELS.SUCCESS: gen_response.success(f'switched to the {num+1}nd song in current playlist'),
            SENTINELS.PLAYER_EMPTY: gen_response.player_empty(f'switch to the {num+1}nd song in current playlist'),
            SENTINELS.VLC_ERROR: gen_response.vlc_error(f'switch to the {num+1}nd song in current playlist'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.player_timeout(f'switch to the {num+1}nd song in current playlist'),
        }[result]
        self.current_song_num = self.player.number
        if result is SENTINELS.SUCCESS:
            response = gen_response.merge(response, self._jump_to_memorized_pos())

        return response
    
    def _toggle_shuffle(self):
        self.shuffle = not self.shuffle
        logger.info(f'Shuffle set to {self.shuffle}')
        if self.shuffle and self.current_song_info is not None:
            random.shuffle(self.shuffle_order)

    def _switch_shuffle(self, direction): # direction: 1 / -1
        if len(self.shuffle_order) > 0:
            shuffle_num = self.shuffle_order.index(self.current_song_num)
            shuffle_num += direction
            if shuffle_num >= len(self.shuffle_order):
                shuffle_num = 0
                random.shuffle(self.shuffle_order)
            elif shuffle_num < 0:
                shuffle_num = len(self.shuffle_order) - 1
            return self.shuffle_order[shuffle_num]
        else:
            return SENTINELS.PLAYER_EMPTY

    def _jump_to_memorized_pos(self):
        path = self.current_song_info[self.current_song_num]['path']
        pos = self.database.get_pos(path)
        if pos is not SENTINELS.POS_NOT_FOUND:
            response = gen_response.success('try to jump to memorized pos')
            response = gen_response.merge(response, self._jump_to_pos(pos), join_char='->')
            return response
        else:
            return gen_response.success(f'no memorized position')

    def _jump_to_pos(self, pos):
        result = self.player.jump_pos(pos)
        return {
            SENTINELS.SUCCESS: gen_response.success(f'jumped to {format_ms(pos)}'),
            SENTINELS.POS_TOO_LATE: gen_response.failed(f'can not jumps to {format_ms(pos)} because it is later than the end of the current song'), 
            SENTINELS.INVALID_PLAYER_STATE: gen_response.not_playing_paused('jump to progress')
        }[result]

    def _replay(self):
        result = self.player.jump_pos(0)
        return {
            SENTINELS.SUCCESS: gen_response.success('jumped to beginning'),
            SENTINELS.POS_TOO_LATE: gen_response.pos_too_late('jump to beginning'), # is this even possible?
            SENTINELS.INVALID_PLAYER_STATE: gen_response.not_playing_paused('jump to beginning')
        }[result]

    def _missing_key(self, action, key):
        logger.error(f'Missed key for action \"{action}\": \"{key}\"')
        return gen_response.missing_key(action, key)

    def _set_current_song(self, info, in_lib=True):
        if not isinstance(info, list):
            info = [info]
        self.current_song_info = info
        self.current_song_in_lib = in_lib
        self.current_song_num = 0
        self.shuffle_order = list(range(len(self.current_song_info)))
        if self.shuffle:
            random.shuffle(self.shuffle_order)
        logger.info(f'Set current info of current songs to {info}, in library {in_lib}')

    def _get_playlist_songs(self, name):
        playlist_id = self.database.get_playlist_via_name(name)
        if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
            ids = self.database.get_playlist_songs(playlist_id)
            if ids is not SENTINELS.PLAYLIST_EMPTY:
                info = self.database.get_song_info(ids)
                info = self.sort_songs(info)
                return info
            else:
                return SENTINELS.PLAYLIST_EMPTY
        else:
            return SENTINELS.PLAYLIST_NOT_FOUND
        
    def sort_songs(self, info):
        return sorted(info, key=lambda x: Path(x['path']).name.lower())
    
    def _get_song(self, alias, cwd): # try to get song id from database
        id = self.database.get_song_via_alias(alias)
        if id is not SENTINELS.ALIAS_NOT_FOUND:
            logger.debug(f'Got ID {id} via alias {alias}')
            return id
        elif cwd is not None:
            path = Path(cwd) / alias
            id = self.database.get_song_via_path(str(path))
            if id is not SENTINELS.SONG_NOT_FOUND:
                logger.debug(f'Got ID {id} via path {path}')
                return id
            else:
                return SENTINELS.NOT_IN_LIB
        else:
            return SENTINELS.MISSING_CWD

    def _add_song(self, path, set_meta=True, bind_alias=True, alias=None, return_id=False):
        song_id = None
        if Path(path).is_file():
            add_response = None
            alias_response = None
            meta_response = None
            auto_alias_response = None
            song_id, ignored = self.database.add_song(path)
            if not ignored:
                add_response = gen_response.success(f'added song \"{path}\" to library')

                # --- manual alias ---
                if alias is not None:
                    result = self.database.bind_alias(song_id, alias)
                    if result is SENTINELS.ALIAS_EXISTS:
                        alias_msg = f'can not bind alias \"{alias}\" to the song'
                    else:
                        alias_msg = f'bound alias \"{alias}\" to the song'
                    alias_response = gen_response.success(alias_msg)
                    
                meta = self._get_meta_from_file(path)

                # --- auto set metadata ---
                if set_meta:
                    count = 0
                    for tag, value in meta.items():
                        self.database.set_song_meta(song_id, tag, value)
                        if value is not None:
                            count += 1
                    meta_response = gen_response.success(f'set {count} metadata of the song from file')
                else:
                    duration = meta.get('duration', None)
                    self.database.set_song_meta(song_id, 'duration', duration)
                    meta_response = gen_response.success(f'set duration to {format_ms(duration)}')

                # --- auto bind alias ---
                if bind_alias:
                    name = meta.get('name', None)
                    if name is not None and not self.database.alias_exists(name):
                        self.database.bind_alias(song_id, name)
                        bind_msg = f'bound alias \"{name}\" from song name in metadata'
                    else:
                        logging.info(f'Name metadata of song with id {song_id} and path {path} does not exist or is already used. Now try to use filename instead')
                        name = Path(path).stem
                        result = self.database.bind_alias(song_id, name)
                        if result is SENTINELS.ALIAS_EXISTS:
                            logging.info(f'Can not find a suitable alias for song with id {song_id} and path {path}. Auto alias binding canceled')
                            bind_msg = f'can not find and bind an available alias for the song automatically'
                        else:
                            bind_msg = f'bound alias \"{name}\" from filename'
                    auto_alias_response = gen_response.success(bind_msg)

                response = gen_response.merge(add_response, alias_response, meta_response, auto_alias_response)
            else:
                response = gen_response.failed(f'can not add \"{path}\" because a song of the same path already exists in library')
        else:
            response = gen_response.invalid_path(path)

        if return_id:
            return song_id, response
        else:
            return response
        
    def _memorize_pos(self):
        while self.running:
            if self.current_song_info is not None and self.player.player.get_state() == vlc.State.Playing:
                path = self.current_song_info[self.current_song_num]['path']
                pos = self.player.get_progress()['time']
                self.database.set_pos(path, pos, log=False)
            sleep(POS_MEMORIZE_INTERVAL)

    def _del_current_pos(self):
        if self.current_song_info is not None:
            path = self.current_song_info[self.current_song_num]['path']
            self.database.del_pos(path)
        else:
            logger.warning('backend:del_current_pos is triggered before any song is loaded')

    def _get_meta_from_file(self, path):
        file = mutagen.File(path, easy=True)
        tags = {}
        if file is not None:
            for file_tag, meta in FILE_META.items():
                tags[meta] = file.get(file_tag, [None])[0]
                if tags[meta] == '':
                    tags[meta] = None

            tags['duration'] = getattr(file.info, 'length', None)

            if tags['duration'] is not None:
                tags['duration'] = int(tags['duration'] * 1000)

            logger.debug(f'Extracted metadata from {path}: {tags}')
            return tags
        else:
            logger.debug(f'Failed to extract metadata from {path} because there is no metadata in the file')
            return {}

    def _scan(self, directory):
        paths = []
        for path in Path(directory).iterdir():
            if path.suffix.lower() in AUDIO_EXTENSIONS and path.is_file():
                paths.append(str(path.resolve()))
        return paths

    def _recurse_scan(self, directory):
        paths = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                path = Path(root) / file
                if path.suffix.lower() in AUDIO_EXTENSIONS:
                    paths.append(str(path.resolve()))
        return paths

    def _listen(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(SERVER_TIMEOUT)
        try:
            server.bind((HOST, PORT))
        except OSError as e:
            self.exit(True, f'Failed to bind to {HOST}:{PORT}: {e}')
        else:
            server.listen(BACKLOG)
            logger.info(f'started listening on {HOST}:{PORT}')
            while self.running:
                try:
                    connection, address = server.accept()
                except socket.timeout:
                    continue

                Thread(target=self._handle_connection, args=(connection,address), daemon=True).start()

    def _handle_connection(self, connection, address):
        request = recv_json(connection)
        if request is not None:
            self.buffer_request(request, connection, address)

    def _play_dead(self): # give some time for daemon-like frontend to exit
        logger.info('Playing dead...')
        sleep(PLAY_DEAD_TIME)
        self.running = False

    def exit(self, error=False, msg=None):
        Thread(target=self.player.stop, daemon=True).start()
        if msg is not None:
            if error:
                logger.critical(msg)
                self.exit_code = 1
            else:
                logger.info(msg)
                self.exit_code = 0
        if error:
            self.running = False
        else:
            self.dying = True
            Thread(target=self._play_dead, daemon=True).start()

if __name__ == '__main__':
    Backend().run()
