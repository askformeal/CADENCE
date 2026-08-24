import sys
import os
import logging
from threading import Thread
import random
import socket
import queue
from time import sleep
from time import time
from pathlib import Path
import vlc
import mutagen

from src import version
from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.constants import DATABASE_PATH, DATABASE_DEV_PATH
from src.constants import BACKLOG, ACTION_KEYS, NON_ACTION_KEYS, IterType, SERVER_TIMEOUT
from src.constants import MAIN_LOOP_INTERVAL, METADATA, FILE_META
from src.constants import PLAY_DEAD_TIME
from src.constants import AUDIO_EXTENSIONS, SOURCES, READABLE_TYPE_NAMES, SEARCH_META
from src.config import CONFIG
from src.sentinels import SENTINELS
from src.connection import recv_json, send_json
from src import gen_response
from src.database import Database
from src.player import Player
from src.pid import add_pid, remove_pid
from src.utils import format_time, parse_time, verify_path_format

logger = setup_logger(__name__, BACKEND_LOG_PATH)

class Backend:
    def __init__(self):
        self.pid = str(os.getpid())
        add_pid(self.pid)

        self.start_time = time()
        self.dev = {'0': False, '1': True}.get(os.environ.get('CADENCE_DEV', '0'), False)
        self.continue_last = {'0': False, '1': True}.get(os.environ.get('CADENCE_CONTINUE', '0'), False)

        if self.dev:
            logger.info('DEVELOPMENT MODE ON')
            database_path = DATABASE_DEV_PATH
        else:
            database_path = DATABASE_PATH

        self.exit_code = 0
        self.running = True
        self.dying = False

        self.loop = False

        self.shuffle = CONFIG.default_shuffle
        self.shuffle_order = []

        self.current_song_info = None
        self.current_song_num = None
        self.current_song_in_lib = False # Use this to prevent KeyError
        self.current_playlist = None
        
        self.dispatch_buffer = queue.Queue() # single way
        self.notifies = []

        try:
            self.database = Database(database_path)
        except RuntimeError as e:
            logger.critical(e)
            self.running = False
        else:
            self.player = Player(self.buffer_request)
            self.notifies.append(f'Welcome to CADENCE, {CONFIG.username}')
            logger.debug(f'{__name__} initiated')

    def run(self):
        if self.running:
            logger.info(f'Command-line Audio Decoding Engine with Navigation and Continuous Execution {version} started, PID: {self.pid}')

            Thread(target=self._listen, daemon=True).start()
            Thread(target=self._memorize_pos, daemon=True).start()
            self._flush_thread = Thread(target=self._flush_buffer, daemon=True)
            self._flush_thread.start()

            if self.continue_last:
                self.buffer_request({'action': 'continue_last', 'source': 'backend'})

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

        else:
            self.exit_code = 1

        remove_pid(self.pid)
        sys.exit(self.exit_code)

    def buffer_request(self, request, connection=None, address=None):            
        if self.dying:
            if connection is not None:
                send_json(connection, gen_response.Dying())
        
        elif request.get('action', None) == 'heartbeat':
            if connection is not None:
                send_json(connection, gen_response.Success('alive'))
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
            try:
                request, connection = self.dispatch_buffer.get()
                if request is SENTINELS.EXIT_FLUSHING:
                    break
                try:
                    response = self.dispatch(request)
                except Exception as e:
                    logger.exception(f'Exception raised when dispatching request')
                    response = gen_response.Failed(f'a CADENCE backend error occurred during dispatching of request: \"{e}\"')

                if connection is not None and request.get('action', None) != 'test_alive':
                    response.notifies = self.notifies.copy()
                    self.notifies = []
                    logger.info(f'Notifies cleared: {response.notifies}')

                if self.dev:
                    response.msg = f'[DEV] {response.msg}'

                logger.info(f'Response: {response}')
                
                if connection is not None:
                    send_json(connection, response)
                    connection.close()
                    logger.info(f'Response sent through socket, connection closed')
            except Exception as e:
                logger.exception(f'Exception raised when handling request')

    def dispatch(self, request):
        response = gen_response.Undefined()
        process_result = self._process_request(request)
        if isinstance(process_result, gen_response.Response) and not process_result.ok():
            response = process_result
        else:
            request = process_result

            action = request['action']
            cwd = request.get('cwd', None)
            # ----------------------------------------------------------------

            if action == 'test_alive':
                response = gen_response.Success('CADENCE backend is running')

            elif action == 'get_notifies':
                response = gen_response.Success('Notifies got')

            elif action == 'status':
                player_status = {
                    vlc.State.Playing: 'playing',
                    vlc.State.Paused: 'paused',
                    vlc.State.Stopped: 'stopped'
                }.get(self.player.player.get_state(), None)

                if self.current_song_info is None:
                    info = {}
                    playlist_len = None
                    current_num = None
                else:
                    info = self.current_song_info[self.current_song_num]
                    playlist_len = len(self.current_song_info)
                    current_num = self.current_song_num

                status = {
                    'path': info.get('path', None),
                    'name': info.get('name', None),
                    'artist': info.get('artist', None),
                    'album': info.get('album', None),
                    'in_library': self.current_song_in_lib,
                    'player_status': player_status,
                    'volume': self.player.volume,
                    'mute': self.player.mute,
                    'playlist_len': playlist_len,
                    'current_num': current_num,
                    'run_time': time() - self.start_time
                }
                progress = self.player.get_progress()
                status['length'] = progress['length']
                status['time'] = progress['time']
                status['dev'] = self.dev
                response = gen_response.Success('status obtained', status)
                
            elif action == 'open':
                song = request['song']
                response = self._open_song(song, cwd)

            elif action == 'play-all':
                response = self._play_all()

            elif action == 'continue_last':
                is_all = self.database.get_setting('last_is_all')
                song = self.database.get_setting('last_song')
                last_cwd = self.database.get_setting('last_cwd')

                if is_all == '1':
                    response = self._play_all()
                else:
                    if song in (SENTINELS.SETTING_NOT_FOUND, None):
                        response = gen_response.Failed('No last song to open')
                    else:
                        response = self._open_song(song, last_cwd)

                logger.debug(response.msg)

            elif action == 'stop':
                response = self._stop_player()

            elif action == 'pause':
                result = self.player.pause()
                response = {
                    SENTINELS.SUCCESS: gen_response.Success('player paused'),
                    SENTINELS.INVALID_PLAYER_STATE: gen_response.Failed('can not pause player because player is not playing'),
                    SENTINELS.VLC_ERROR: gen_response.VLCError('pause player'),
                    SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('pause player')
                }[result]

            elif action == 'resume':
                result = self.player.resume()
                response = {
                    SENTINELS.SUCCESS: gen_response.Success('player resumed'),
                    SENTINELS.INVALID_PLAYER_STATE: gen_response.Failed('can not resume player because player is not paused'),
                    SENTINELS.VLC_ERROR: gen_response.VLCError('resume player'),
                    SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('resume player')
                }[result]

            elif action == 'toggle':
                result = self.player.toggle()
                response = {
                    SENTINELS.SUCCESS: gen_response.Success('player toggled'),
                    SENTINELS.INVALID_PLAYER_STATE: gen_response.NotPlayingPaused('toggle player'),
                    SENTINELS.VLC_ERROR: gen_response.VLCError('toggle player'),
                    SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('toggle player')
                }[result]

            elif action == 'list':
                response = gen_response.Success('obtained current playlist')
                if self.current_song_info is not None:
                    response.attachment = self.current_song_info.copy()
                else:
                    response.attachment = []

            elif action == 'shuffle':
                self._toggle_shuffle()
                mode = {True: 'on', False: 'off'}[self.shuffle]
                response = gen_response.Success(f"shuffle mode turned {mode}")

            elif action == 'loop':
                self.loop = not self.loop
                mode = {True: 'on', False: 'off'}[self.loop]
                response = gen_response.Success(f'loop mode turned {mode}')

            elif action == 'dice':
                if self.current_song_info is None:
                    response = gen_response.PlayerEmpty('switch to a random song in current playlist')
                elif len(self.current_song_info) == 1:
                    response = gen_response.Failed('can not switch to a random song because there is only one song in current playlist ')
                else:
                    pool = list(range(len(self.current_song_info)))
                    pool.remove(self.current_song_num)
                    num = random.choice(pool)
                    result = self.player.load_number(num)

                    if result is SENTINELS.SUCCESS:
                        self._set_current_num(self.player.number)

                    response = {
                        SENTINELS.SUCCESS: gen_response.Success(f'diced to the {num+1}nd song in current playlist: {self._get_output_current_name()}'),
                        SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty(f'switch to the {num+1}nd song in current playlist'),
                        SENTINELS.VLC_ERROR: gen_response.VLCError(f'switch to the {num+1}nd song in current playlist'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout(f'switch to the {num+1}nd song in current playlist'),
                    }[result]

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
                
                if result is SENTINELS.SUCCESS:
                    self._set_current_num(self.player.number)

                response = {
                    SENTINELS.SUCCESS: gen_response.Success(f'switched to previous song: {self._get_output_current_name()}'),
                    SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty('switch to previous song'),
                    SENTINELS.VLC_ERROR: gen_response.VLCError('switch to previous song'),
                    SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('switch to previous song')
                }[result]
                if result is SENTINELS.SUCCESS:
                    response += self._replay()

            elif action == 'next':
                on_end = request['on_end']
                if on_end:
                    self._del_current_pos()

                if on_end and self.loop:
                    result = self.player.load_number(self.player.number)
                    response = {
                        SENTINELS.SUCCESS: gen_response.Success('replayed current song'),
                        SENTINELS.VLC_ERROR: gen_response.VLCError('replayed current song'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('replayed current song'),
                    }[result]
                else:
                    if self.shuffle:
                        result = self.player.load_number(self._switch_shuffle(1))
                    else:
                        result = self.player.switch_next()

                    if result is SENTINELS.SUCCESS:
                        self._set_current_num(self.player.number)

                    response = {
                        SENTINELS.SUCCESS: gen_response.Success(f'switched to next song: {self._get_output_current_name()}'),
                        SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty('switch to next song'),
                        SENTINELS.VLC_ERROR: gen_response.VLCError('switch to next song'),
                        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('switch to next song')
                    }[result]
                    if result is SENTINELS.SUCCESS:
                        response += self._replay()

            elif action == 'seek':
                raw_time = request['time']
                pos = parse_time(raw_time)
                if pos is SENTINELS.INVALID_TIME:
                    response = gen_response.Failed(f'invalid time: {raw_time}')
                else:
                    response = self._jump_to_pos(pos)

            elif action == 'jump':
                percent = request['progress']
                if percent < 0:
                    response = gen_response.PercentageTooLow(percent)
                elif percent > 100:
                    response = gen_response.PercentageTooHigh(percent)
                else:
                    length = self.player.get_progress()['length']
                    if length == -1:
                        response = gen_response.NotPlayingPaused('jump to progress')
                    else:
                        pos = length * (percent / 100)
                        response = self._jump_to_pos(pos)
            elif action == 'replay':
                response = self._replay()
                if response.ok():
                    self._del_current_pos()

            elif action == 'volume':
                volume = request['volume']
                if volume < 0:
                    response = gen_response.PercentageTooLow(volume)
                elif volume > 100:
                    response = gen_response.PercentageTooHigh(volume)
                else:
                    self.player.set_volume(volume)
                    response = gen_response.Success(f'set volume to {self.player.volume}%')

            elif action == 'mute':
                self.player.set_mute(not self.player.mute)
                mode = {True: 'on', False: 'off'}[self.player.mute]
                response = gen_response.Success(f'turned mute mode {mode}')

            elif action == 'lib.info':
                songs = request['songs']
                show_aliases = request['show_aliases']
                show_playlists = request['show_playlists']

                failed = []
                info = []

                for song in songs:
                    song_id = self._get_song(song, cwd)
                    if song_id is SENTINELS.MISSING_CWD:
                        failed.append(gen_response.MissingCWD('lib.info'))
                    elif song_id is SENTINELS.NOT_IN_LIB:
                        failed.append(gen_response.SongNotExist(f'get information of song \"{song}\"'))
                    else:
                        song_info = self.database.get_song_info(song_id)[0]

                        if show_aliases:
                            aliases = self.database.get_song_aliases(song_id)
                            song_info['aliases'] = aliases

                        if show_playlists:
                            playlist_ids = self.database.get_song_playlists(song_id)
                            playlist_info = self.database.get_playlists_info(playlist_ids)
                            playlist_names = list(map(lambda pl: pl['name'], playlist_info))
                            song_info['playlists'] = playlist_names

                        info.append(song_info)

                msg = f'got information of [{len(info)}/{len(songs)}] songs'
                if len(info) > 0 or len(songs) == 0:
                    response = gen_response.Success(msg, attachment=info, failed=failed)
                else:
                    response = gen_response.Failed(msg, failed=failed)

            elif action == 'lib.list':
                info = self.database.get_all_song_info()
                if request['show_aliases']:
                    info = self._add_songs_aliases(info)

                if request['show_playlists']:
                    info = self._add_songs_playlist_names(info)

                response = gen_response.Success('obtained information of all songs in library', self._sort_songs(info))

            elif action == 'lib.search':
                keywords = request['keyword']
                keywords = list(map(lambda k:k.lower(), keywords))
                is_or = request['or']

                results = []

                info = self.database.get_all_song_info()
                song_ids = list(map(lambda s: s['id'], info))
                aliases = {}
                if len(song_ids) > 0:
                    for song_id, alias in self.database.get_multi_song_aliases(song_ids):
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

                response = gen_response.Success(f'{len(results)} result(s) found in library', results)

            elif action == 'lib.add':
                paths = request['paths']
                aliases = request['aliases']
                loose_path = request['loose_path']

                set_meta = not request['skip_meta']
                bind_alias = not request['skip_alias']
                if len(paths) == 0:
                    response = gen_response.EmptyList('paths')
                elif len(paths) != len(aliases) and len(aliases) > 0:
                    response = gen_response.Failed('can not add song(s) because the provided number of paths and aliases are not the same')
                else:
                    if len(aliases) == 0:
                        aliases = [None] * len(paths)
                    failed = []
                    succeed = [] # otherwise all the info about auto meta and alias will be lost
                    for path, alias in zip(paths, aliases):
                        add_response = self._add_song(path, set_meta, bind_alias, alias, cwd=cwd, loose_path=loose_path)
                        if add_response.ok():
                            succeed.append(add_response)
                        else:
                            failed.append(add_response)
                    
                    response = gen_response.BatchAuto('songs added to library', len(failed), len(paths), attachment=succeed, failed=failed)

            elif action == 'lib.del':
                songs = request['songs']

                if len(songs) == 0:
                    response = gen_response.EmptyList('songs')
                else:
                    failed = []

                    for song in songs:
                        id = self._get_song(song, cwd)
                        if id is SENTINELS.MISSING_CWD:
                            failed.append(gen_response.MissingCWD('lib.del'))
                        elif id is SENTINELS.NOT_IN_LIB:
                            failed.append(gen_response.SongNotExist(f'delete {song}'))
                        else:
                            path = self.database.get_song_info(id)[0]['path']
                            if self.current_song_info is not None and self.current_song_info[self.current_song_num].get('id', None) == id:
                                self.current_song_info[self.current_song_num] = {'path': path} 
                                self.current_song_in_lib = False

                            self.database.delete_song(id)

                    response = gen_response.BatchAuto('songs removed from library', len(failed), len(songs), failed=failed)

            elif action == 'lib.prune':
                dry_run = request['dry_run']
                info = self.database.get_all_song_info()
                found = []
                for song in info:
                    if not Path(song['path']).is_file():
                        found.append(song)
                if dry_run:
                    response = gen_response.Success(f'{len(found)} song(s) with unavailable path(s) found in library', attachment=found)
                else:
                    failed = []
                    for song in found:
                        self.database.delete_song(song['id'])
                        del_response = self._remove_from_current(song['path'])
                        if not del_response.ok():
                            failed.append(del_response)
                    
                    response = gen_response.Success(f'{len(found)} song(s) with unavailable path(s) found and was removed from library', attachment=found, failed=failed)

            elif action == 'lib.scan':
                missing_cwd = False
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

                    failed_responses = []

                    if Path(directory).is_dir():
                        if is_recurse:
                            paths = self._recurse_scan(directory)
                        else:
                            paths = self._scan(directory)

                        if len(paths) == 0:
                            response = gen_response.Success(f'No supported audio file found under {directory}', attachment=[])
                        else:
                            if dry_run:
                                response = gen_response.Success(f'{len(paths)} supported audio files found under {directory}', paths)
                            else:
                                ids = []
                                for path in paths:
                                    song_id, add_response = self._add_song(path, set_meta, bind_alias, return_id=True)
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
                                    playlist_id = self.database.get_playlist_via_name(playlist)
                                    if playlist_id is SENTINELS.PLAYLIST_NOT_FOUND:
                                        playlist_msg = f'can not add songs to playlist \"{playlist}\" because it does not exist'
                                    else:
                                        for song_id in ids:
                                            self.database.add_song_to_playlist(playlist_id, song_id) # all songs are freshly added, no chance of ignored

                                        playlist_msg = f'added {len(ids)} song(s) to playlist {playlist}'
                                    response += gen_response.Success(playlist_msg)

                    else:
                        response = gen_response.Failed(f'\"{directory}\" is not a valid directory')

            elif action == 'lib.reset':
                self.database.reset()
                if self.current_song_in_lib:
                    path = self.current_song_info[self.current_song_num]['path']
                    self._set_current_song({'path': path}, False)
                response = gen_response.Success('database reset')

            elif action == 'lib.meta.set':
                song_id = self._get_song(request['song'], cwd)
                if song_id is SENTINELS.MISSING_CWD:
                    response = gen_response.MissingCWD('lib.meta.set')
                elif song_id is SENTINELS.NOT_IN_LIB:
                    response = gen_response.SongNotExist(f"set metadata of \"{request['song']}\"")
                else:
                    metadata = {}
                    for label in METADATA:
                        metadata[label] = request[label]

                    if True in map(lambda x: x is not None, metadata.values()): # not all meta is none
                        for label, value in metadata.items():
                            if value is not None:
                                if value == '':
                                    value = SENTINELS.CLEAR_META
                                self.database.set_song_meta(song_id, label, value)

                        response = gen_response.Success('metadata set')

                    else:
                        response = gen_response.Failed(f'can not set metadata because no metadata was provided')

            elif action == 'lib.meta.read-file':
                song = request['song']
                song_id = self._get_song(song, cwd)
                set_all = request['all']
                if song_id is SENTINELS.MISSING_CWD:
                    response = gen_response.MissingCWD('lib.meta.read-file')
                elif song_id is SENTINELS.NOT_IN_LIB:
                    response = gen_response.SongNotExist(f"set metadata of \"{song}\"")
                else:
                    count = 0
                    path = self.database.get_song_info(song_id)[0]['path']
                    file_meta = self._get_meta_from_file(path)
                    for label, value in file_meta.items():
                        if value not in ('', None) and (request[label] or set_all):
                            self.database.set_song_meta(song_id, label, value)
                            count += 1
                    response = gen_response.Success(f'{count} metadata set')

            elif action == 'lib.alias.list':
                song = request['song']
                id = self._get_song(song, cwd)
                if id is SENTINELS.MISSING_CWD:
                    response = gen_response.MissingCWD('lib.alias.list')
                elif id is not SENTINELS.NOT_IN_LIB:
                    aliases = self.database.get_song_aliases(id)
                    response = gen_response.Success('obtained all aliases in library', aliases)
                else:
                    response = gen_response.SongNotExist(f'show aliases of {song}')

            elif action == 'lib.alias.bind':
                song = request['song']
                aliases = request['aliases']
                if len(aliases) == 0:
                    response = gen_response.EmptyList('aliases')
                else:
                    id = self._get_song(song, cwd)

                    if id is SENTINELS.MISSING_CWD:
                        response = gen_response.MissingCWD('lib.alias.bind')
                    elif id is SENTINELS.NOT_IN_LIB:
                        response = gen_response.SongNotExist(f'bind alias to {song}')
                    else:
                        failed = []
                        for alias in aliases:
                            result = self.database.bind_alias(id, alias)
                            bind_response = {
                                SENTINELS.SUCCESS: gen_response.Success(f"bound alias \"{alias}\" to song \"{song}\""),
                                SENTINELS.ALIAS_EXISTS: gen_response.Failed(f'can not bind alias \"{alias}\" because it is already bound to another song in library'),
                                SENTINELS.SONG_NOT_FOUND: gen_response.SongNotExist(f'bind alias to \"{song}\"') # not really necessary, but Monica insists
                            }[result]
                            if not bind_response.ok():
                                failed.append(bind_response)

                        response = gen_response.BatchAuto('aliases bound to song', len(failed), len(aliases), failed=failed)

            elif action == 'lib.alias.unbind':
                aliases = request['aliases']

                if len(aliases) == 0:
                    response = gen_response.EmptyList('aliases')
                else:
                    failed = []

                    for alias in aliases:
                        result = self.database.unbind_alias(alias)
                        if result is SENTINELS.ALIAS_NOT_FOUND:
                            failed.append(gen_response.Failed(f'can not unbind {alias} because it does not exist in library'))

                    response = gen_response.BatchAuto('aliases unbound', len(failed), len(aliases), failed=failed)

            elif action == 'lib.playlist.list':
                response = gen_response.Success('obtained list of playlist in library')

                playlist = request['playlist']
                if playlist is not None:
                    info = self._get_playlist_songs(playlist)
                    if info is SENTINELS.PLAYLIST_NOT_FOUND:
                        response = gen_response.PlaylistNotExist(f'list songs of playlist \"{playlist}\"')
                    elif info is SENTINELS.PLAYLIST_EMPTY:
                        response.attachment = []
                    else:
                        if request['show_aliases']:
                            info = self._add_songs_aliases(info)

                        if request['show_playlists']:
                            info = self._add_songs_playlist_names(info)

                        response.attachment = info
                else:
                    playlists = self.database.get_all_playlists()
                    response.attachment = playlists

            elif action == 'lib.playlist.create':
                name = request['name']
                ignored = self.database.create_playlist(name)[1]
                if not ignored:
                    response = gen_response.Success(f'created playlist \"{name}\"')
                else:
                    response = gen_response.Failed(f'can not create \"{name}\" because a playlist of the same name already exists in library')

            elif action == 'lib.playlist.add':
                playlist = request['playlist']
                songs = request['songs']

                if len(songs) == 0:
                    response = gen_response.EmptyList('songs')
                else:
                    playlist_id = self.database.get_playlist_via_name(playlist)

                    if playlist_id is SENTINELS.PLAYLIST_NOT_FOUND:
                        response = gen_response.PlaylistNotExist(f'add song to playlist \"{request['playlist']}\"')
                    else:
                        failed = []
                        for song in songs:
                            song_id = self._get_song(song, cwd)
                            if song_id is SENTINELS.MISSING_CWD:
                                failed.append(gen_response.MissingKey('lib.playlist.add', 'cwd'))
                            elif song_id is SENTINELS.NOT_IN_LIB:
                                failed.append(gen_response.SongNotExist(f'add song \"{song}\" to playlist \"{playlist}\"'))
                            else:
                                ignored = self.database.add_song_to_playlist(playlist_id, song_id)
                                if ignored:
                                    failed.append(gen_response.Failed(f'can not add song \"{song}\" to playlist \"{playlist}\" because it is already in the playlist'))

                        response = gen_response.BatchAuto('songs added to playlist', len(failed), len(songs), failed=failed)                                            

            elif action == 'lib.playlist.kick':
                playlist = request['playlist']
                songs = request['songs']

                if len(songs) == 0:
                    response = gen_response.EmptyList('songs')
                else:                    
                    playlist_id = self.database.get_playlist_via_name(playlist)
                    if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
                        failed = []
                        for song in songs:
                            song_id = self._get_song(song, cwd)
                            if song_id is SENTINELS.MISSING_CWD:
                                failed.append(gen_response.MissingKey('lib.playlist.kick', 'cwd'))
                            elif song_id is SENTINELS.NOT_IN_LIB:
                                failed.append(gen_response.SongNotExist(f'remove song \"{song}\" from playlist \"{playlist}\"'))
                            else:
                                result = self.database.del_song_from_playlist(playlist_id, song_id)
                                if result is SENTINELS.PLAYLIST_SONG_NOT_FOUND:
                                    failed.append(gen_response.Failed(f"can not remove song \"{song}\" from playlist \"{playlist}\" because the song is not in the playlist"))

                        response = gen_response.BatchAuto('songs removed from playlist', len(failed), len(songs), failed=failed)
                    else:
                        response = gen_response.PlaylistNotExist(f"remove song(s) from playlist {playlist}")

            elif action == 'lib.playlist.del':
                playlist_id = self.database.get_playlist_via_name(request['playlist'])
                if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
                    self.database.del_playlist(playlist_id)
                    response = gen_response.Success(f"deleted playlist \"{request['playlist']}\"")
                else:
                    response = gen_response.PlaylistNotExist(f"delete playlist \"{request['playlist']}\"")

            elif action == 'config.show':
                option = request['option']
                value, source = CONFIG.get_option(option)

                if value is SENTINELS.UNKNOWN_OPTION:
                    response = gen_response.OptionNotExist(f'get value of {option}')
                else:
                    source = {
                        SENTINELS.FROM_DEFAULT: 'default value',
                        SENTINELS.FROM_FILE: 'configure file'
                    }[source]
                    response = gen_response.Success(f'Got value of {option}', {'value': value, 'source': source})

            elif action == 'config.set':
                option = request['option']
                value = request['value']
                overwrite_corrupt = request['overwrite_corrupt']

                result = CONFIG.set_option(option, value, overwrite_corrupt=overwrite_corrupt)
                response = {
                    SENTINELS.SUCCESS: gen_response.Success(f'Set value of {option} to \"{value}\"'),
                    SENTINELS.UNKNOWN_OPTION: gen_response.OptionNotExist(f'set value of {option}'),
                    SENTINELS.INVALID_CONFIG_FILE: gen_response.Failed(f'can not set value of option because configure file is corrupted. You can try again with the --overwrite-corrupt option to overwrite it'),
                    SENTINELS.INVALID_OPTION_VALUE: gen_response.Failed(f'can not set value of option because the provided value is not valid'),
                    SENTINELS.FILE_IO_FAILED: gen_response.Failed(f'can not set value of option because failed to write into configure file')
                }[result]

            elif action == 'config.unset':
                option = request['option']

                result = CONFIG.unset_option(option)
                response = {
                    SENTINELS.SUCCESS: gen_response.Success(f'Unset value of {option}'),
                    SENTINELS.UNKNOWN_OPTION: gen_response.OptionNotExist(f'unset value of {option}'),
                    SENTINELS.INVALID_CONFIG_FILE: gen_response.Failed(f'can not unset value of option because configure file is corrupted'),
                    SENTINELS.OPTION_NOT_FOUND: gen_response.Failed(f'can not unset value of option because it is not set in configure file'),
                    SENTINELS.FILE_IO_FAILED: gen_response.Failed(f'can not unset value of option because failed to write into configure file')
                }[result]

            elif action == 'exit':
                self.exit()
                response = gen_response.Success('CADENCE backend is now exiting')
            else:
                logger.error(f'Invalid \"action\" value received: {action}')
                response = gen_response.UnknownAction(action)

        return response

    def _process_request(self, request) -> dict | gen_response.Response:
        action = request.get('action', None)        
        if action is None:
            logger.error('Not \"action\" key found in request')
            return gen_response.MissingKey('all', 'action')
        
        else:
            keys = ACTION_KEYS.get(action, {})

            expected_keys = set(keys.keys()) | NON_ACTION_KEYS
            unexpected_keys = set(request.keys()) - expected_keys
            if len(unexpected_keys) > 0:
                logger.warning(f'Unexpected key(s) received: {unexpected_keys}')

            for key, info in keys.items():
                key_type, is_required = info[:2]
                value = request.get(key, SENTINELS.KEY_NOT_PROVIDED)
                if value is SENTINELS.KEY_NOT_PROVIDED:
                    if is_required:
                        return gen_response.MissingKey(action, key)
                    else:
                        try:
                            default_value = info[2]
                        except IndexError:
                            return gen_response.Failed(f'Value of key \"{key}\" was not provided and not default value is available. Please report this error')
                        else:
                            request[key] = default_value
                else:
                    if isinstance(key_type, IterType): # (iter_type, element_type)
                        # verify iterable type
                        element_type = key_type.element_type
                        if isinstance(value, (list, tuple)):
                            for element in value:
                                if not isinstance(element, element_type):
                                    return gen_response.InvalidElementType(action, key, READABLE_TYPE_NAMES[element_type], type(element).__name__)
                        elif not (value is None and not is_required):
                            return gen_response.InvalidKeyType(action, key, READABLE_TYPE_NAMES[IterType], type(value).__name__)
                        
                    elif not isinstance(value, key_type) and not (value is None and not is_required): # None type acceptable for non-required keys even if not stated in ACTION_KEYS
                        return gen_response.InvalidKeyType(action, key, READABLE_TYPE_NAMES[key_type], type(value).__name__)

            return request

    def _open_song(self, song, cwd=None) -> gen_response.Response:
        info_to_set = None
        paths_to_load = None # MUST be a list!!!
        playlist_id = None
        
        id = self._get_song(song, cwd)
        if id is SENTINELS.MISSING_CWD:
            response = gen_response.MissingCWD('open')
        elif id is not SENTINELS.NOT_IN_LIB:
            # open single song by path / alias
            info_to_set = (self.database.get_song_info(id),)
            paths_to_load = [info_to_set[0][0]['path']]
        else:
            path = Path(cwd) / song
            info, playlist_id = self._get_playlist_songs(song, return_id=True)
            if info is SENTINELS.PLAYLIST_EMPTY:
                playlist_id = None
                response = gen_response.Failed(f'can not open playlist \"{song}\" because it is empty')

            elif info is not SENTINELS.PLAYLIST_NOT_FOUND:
                # open playlist
                info_to_set = (info,)
                paths_to_load = list(map(lambda i: i['path'], info))

            else:
                # Not in library, try to open as path
                playlist_id = None
                if path.is_file():
                    info_to_set = ([{'path': str(path)}], False)
                    paths_to_load = [str(path)]
                else:
                    logger.warning(f'Can not open {path}')
                    response = gen_response.InvalidPath(str(path))

        if paths_to_load is not None:
            if self.current_song_info is None:
                current_paths = []
            else:
                current_paths = list(map(lambda s: s['path'], self.current_song_info))

            if len(paths_to_load) == 1 and paths_to_load[0] in current_paths:
                num = current_paths.index(paths_to_load[0])
                response = gen_response.Success('song in current playlist. try to switch')
                response.append(self._switch_song(num), joiner='->')
            else:
                self._set_current_song(*info_to_set)
                response = self._load_paths(paths_to_load, song)

                if response.ok():
                    self._save_last_song(song, cwd)
                    self.current_playlist = playlist_id
                    if playlist_id is not None:
                        last_num = self.database.get_playlist_last_num(playlist_id)
                        if last_num not in (None, SENTINELS.PLAYLIST_NOT_FOUND):
                            response += gen_response.Success('last played number detected, switching')
                            response.append(self._switch_song(last_num), joiner='->')
                        else:
                            self._set_current_num(0)

        return response

    def _load_paths(self, paths, song, jump_to_mem=True) -> gen_response.Response:
        result = self.player.load_paths(paths)
        response = {
            SENTINELS.SUCCESS: gen_response.Success(f'opened song/playlist \"{song}\"'),
            SENTINELS.PLAYER_LOAD_EMPTY: gen_response.Failed('can not load empty list of songs'),
            SENTINELS.VLC_ERROR: gen_response.VLCError('load path(s)'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('load path(s)'),
        }[result]
        if jump_to_mem and result is SENTINELS.SUCCESS:
            response += self._jump_to_memorized_pos()
        return response

    def _play_all(self):
        info = self.database.get_all_song_info()
        if len(info) > 0:
            info = self._sort_songs(info)
            self._set_current_song(info, True)
            paths = list(map(lambda x: x['path'], info))
            response = self._load_paths(paths, 'all-songs')
            if response.ok():
                self.database.set_setting('last_is_all', '1')
                self.current_playlist = SENTINELS.PLAY_ALL
                last_num = self.database.get_setting('last_play_all_num')
                if last_num not in (SENTINELS.SETTING_NOT_FOUND, None):
                    last_num = int(last_num)

                    response += gen_response.Success('last played number detected, switching')
                    response.append(self._switch_song(last_num), joiner='->')
                else:
                    self._set_current_num(0)
        else:
            response = gen_response.Failed('can not open all songs because there is none in library')
        return response

    def _stop_player(self) -> gen_response.Response:
        result = self.player.stop()
        return {
            SENTINELS.SUCCESS: gen_response.Success('player stopped'),
            SENTINELS.VLC_ERROR: gen_response.VLCError('stop player'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('stop player')
        }[result]

    def _remove_from_current(self, path) -> gen_response.Response:
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
                    response += self._switch_song(num)
                    return response
                else:
                    self.current_song_info = None
                    self.current_song_num = None
                    self.current_song_in_lib = False
                    self.current_playlist = None
                    return self._stop_player()
            else:
                return gen_response.Success('path not in current playlist') # not that anyone will actually read this but, you know, for good measure
        else:
            return gen_response.Success('current playlist empty') # same as above

    def _switch_song(self, num) -> gen_response.Response:
        max_num = len(self.player.medias)
        if num >= max_num:
            num_to_load = max_num - 1 # 9999999999 will switch the last song
        elif num < 0:
            num_to_load = max(max_num + num, 0) # -3 will switch the third from last song, -9999999999 will switch to the first song
        else:
            num_to_load = num
        result = self.player.load_number(num_to_load)

        if result is SENTINELS.SUCCESS:
            self._set_current_num(self.player.number)

        response = {
            SENTINELS.SUCCESS: gen_response.Success(f'switched to the {num+1}nd song in current playlist: {self._get_output_current_name()}'),
            SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty(f'switch to the {num+1}nd song in current playlist'),
            SENTINELS.VLC_ERROR: gen_response.VLCError(f'switch to the {num+1}nd song in current playlist'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout(f'switch to the {num+1}nd song in current playlist'),
        }[result]
        if result is SENTINELS.SUCCESS:
            response += self._jump_to_memorized_pos()

        return response

    def _set_current_num(self, num, update_database=True):
        self.current_song_num = num

        if update_database and self.current_playlist is not None:
            if self.current_playlist is SENTINELS.PLAY_ALL:
                self.database.set_setting('last_play_all_num', num)
            else:
                self.database.set_playlist_last_num(self.current_playlist, num)

        logger.info(f'Updated current playlist number to {num}')
    
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

    def _jump_to_memorized_pos(self) -> gen_response.Response:
        path = self.current_song_info[self.current_song_num]['path']
        pos = self.database.get_pos(path)
        if pos is not SENTINELS.POS_NOT_FOUND:
            response = gen_response.Success('try to jump to memorized pos')
            response.append(self._jump_to_pos(pos), joiner='->')
            return response
        else:
            return gen_response.Success(f'no memorized position')

    def _jump_to_pos(self, pos) -> gen_response.Response:
        result = self.player.jump_pos(pos)
        return {
            SENTINELS.SUCCESS: gen_response.Success(f'jumped to {format_time(pos)}'),
            SENTINELS.POS_TOO_LATE: gen_response.Failed(f'can not jumps to {format_time(pos)} because it is later than the end of the current song'), 
            SENTINELS.INVALID_PLAYER_STATE: gen_response.NotPlayingPaused('jump to progress')
        }[result]

    def _replay(self) -> gen_response.Response:
        result = self.player.jump_pos(0)
        return {
            SENTINELS.SUCCESS: gen_response.Success('jumped to beginning'),
            SENTINELS.POS_TOO_LATE: gen_response.PosTooLate('jump to beginning'), # is this even possible?
            SENTINELS.INVALID_PLAYER_STATE: gen_response.NotPlayingPaused('jump to beginning')
        }[result]

    def _set_current_song(self, info, in_lib=True):
        if not isinstance(info, list):
            info = [info]
        self.current_song_info = info
        self.current_song_in_lib = in_lib
        self._set_current_num(0, update_database=False)
        self.shuffle_order = list(range(len(self.current_song_info)))
        if self.shuffle:
            random.shuffle(self.shuffle_order)
        logger.info(f'Set current info of current songs to {info}, in library {in_lib}')

    def _get_playlist_songs(self, name, return_id=False):
        playlist_id = self.database.get_playlist_via_name(name)
        if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
            ids = self.database.get_playlist_songs(playlist_id)
            if ids is not SENTINELS.PLAYLIST_EMPTY:
                info = self.database.get_song_info(ids)
                info = self._sort_songs(info)
                result = info
            else:
                result = SENTINELS.PLAYLIST_EMPTY
        else:
            result = SENTINELS.PLAYLIST_NOT_FOUND

        if return_id:
            return result, playlist_id
        else:
            return result
        
    def _sort_songs(self, info):
        return sorted(info, key=lambda x: Path(x['path']).name.lower())
    
    def _get_song(self, song, cwd): # try to get song id from database
        id = self.database.get_song_via_alias(song)
        if id is not SENTINELS.ALIAS_NOT_FOUND:
            logger.debug(f'Got song ID {id} via alias {song}')
            return id

        elif song.isdecimal() and self.database.song_exists(int(song)): # isdecimal rules out floats
            logger.debug(f'Got song ID {int(song)} via song ID') # sure, why not
            return int(song)

        elif cwd is not None:
            path = Path(cwd) / song
            id = self.database.get_song_via_path(str(path))
            if id is not SENTINELS.SONG_NOT_FOUND:
                logger.debug(f'Got song ID {id} via path {path}')
                return id
            else:
                return SENTINELS.NOT_IN_LIB
        else:
            return SENTINELS.MISSING_CWD

    def _get_output_current_name(self):
        if self.current_song_info is None or self.current_song_num >= len(self.current_song_info):
            return 'no song playing'
        else:
            return self._get_output_song_name(self.current_song_info[self.current_song_num])

    def _get_output_song_name(self, info):
        name = info.get('name', None)
        if name is None:
            name = Path(info['path']).stem
        return name

    def _add_songs_aliases(self, info):
        for i, song in enumerate(info):
            aliases = self.database.get_song_aliases(song['id'])
            info[i]['aliases'] = aliases
        return info

    def _add_songs_playlist_names(self, info):
        for i, song in enumerate(info):
            playlists_id = self.database.get_song_playlists(song['id'])
            playlists_info = self.database.get_playlists_info(playlists_id)
            info[i]['playlists'] = list(map(lambda pl: pl['name'], playlists_info))
        return info

    def _add_song(self, path, set_meta=True, bind_alias=True, alias=None, cwd=None, loose_path=False, return_id=False) -> tuple[int, gen_response.Response] | gen_response.Response:
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
            song_id, ignored = self.database.add_song(path)
            if not ignored:
                add_response = gen_response.Success(f'added song \"{path}\" to library')

                # --- manual alias ---
                if alias is not None:
                    result = self.database.bind_alias(song_id, alias)
                    if result is SENTINELS.ALIAS_EXISTS:
                        alias_msg = f'can not bind alias \"{alias}\" to the song'
                    else:
                        alias_msg = f'bound alias \"{alias}\" to the song'
                    alias_response = gen_response.Success(alias_msg)
                    
                meta = self._get_meta_from_file(path)

                # --- auto set metadata ---
                if set_meta:
                    count = 0
                    for tag, value in meta.items():
                        self.database.set_song_meta(song_id, tag, value)
                        if value is not None:
                            count += 1
                    meta_response = gen_response.Success(f'set {count} metadata of the song from file')
                else:
                    duration = meta.get('duration', None)
                    bitrate = meta.get('bitrate', None)
                    sample_rate = meta.get('sample_rate', None)
                    channels = meta.get('channels', None)
                    
                    self.database.set_song_meta(song_id, 'duration', duration)
                    self.database.set_song_meta(song_id, 'bitrate', bitrate)
                    self.database.set_song_meta(song_id, 'sample_rate', sample_rate)
                    self.database.set_song_meta(song_id, 'channels', channels)

                    meta_response = gen_response.Success(f'set duration to {format_time(duration)}, bitrate to {bitrate}, sample rate to {sample_rate} and channels to {channels}')

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
                    auto_alias_response = gen_response.Success(bind_msg)

                response = add_response + alias_response + meta_response + auto_alias_response
            else:
                response = gen_response.Failed(f'can not add \"{path}\" because a song of the same path already exists in library')
        else:
            response = gen_response.InvalidPath(path)

        if return_id:
            return song_id, response
        else:
            return response

    def _del_current_pos(self):
        if self.current_song_info is not None:
            path = self.current_song_info[self.current_song_num]['path']
            self.database.del_pos(path)
        else:
            logger.warning('backend:del_current_pos is triggered before any song is loaded')

    def _get_meta_from_file(self, path):
        try:
            file = mutagen.File(path, easy=True)
        except (OSError, mutagen.MutagenError):
            logger.debug(f'Failed to extract metadata from {path} because it is not accessible')
            return {}
        else:
            tags = {}
            if file is not None:
                for file_tag, meta in FILE_META.items():
                    tags[meta] = file.get(file_tag, [None])[0]
                    if tags[meta] == '':
                        tags[meta] = None

                tags['duration'] = getattr(file.info, 'length', None)
                tags['bitrate'] = getattr(file.info, 'bitrate', None)
                tags['sample_rate'] = getattr(file.info, 'sample_rate', None)
                tags['channels'] = getattr(file.info, 'channels', None)

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

    def _save_last_song(self, song, cwd):
        self.database.set_setting('last_is_all', '0')
        self.database.set_setting('last_song', song)
        self.database.set_setting('last_cwd', cwd)

    def _memorize_pos(self):
        while self.running:
            if self.current_song_info is not None and self.player.player.get_state() == vlc.State.Playing:
                path = self.current_song_info[self.current_song_num]['path']
                pos = self.player.get_progress()['time']
                self.database.set_pos(path, pos, log=False)
            sleep(CONFIG.pos_memorize_interval)

    def _listen(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(SERVER_TIMEOUT)
        host = CONFIG.host
        port = CONFIG.port
        try:
            server.bind((host, port))
        except OSError as e:
            self.exit(True, f'Failed to bind to {port}:{host}: {e}')
        else:
            server.listen(BACKLOG)
            logger.info(f'started listening on {host}:{port}')
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
