import sys
import logging
from threading import Thread
import socket
import queue
from time import sleep
from pathlib import Path
import vlc

from src import version
from src.constants import LOG_PATH, FILE_LOG_LEVEL, CONSOLE_LOG_LEVEL, LOG_ENCODING
from src.constants import HOST, PORT, BACKLOG, REQUIRED_KEYS, SERVER_TIMEOUT
from src.constants import MAIN_LOOP_INTERVAL
from src.sentinels import SENTINELS
from src.connection import recv_json, send_json
from src.response import response_template
from src.database import Database
from src.player import Player

console = logging.StreamHandler()
console.setLevel(CONSOLE_LOG_LEVEL)

logger = logging.getLogger(__name__)
class Backend:
    def __init__(self):
        self.exit_code = 0
        self._setup_logging()
        self.running = True
        self.current_song_info = None
        self.current_song_num = None
        self.current_song_in_lib = False # Use this to prevent KeyError
        self.dispatch_buffer = queue.Queue() # single way
        try:
            self.database = Database()
        except RuntimeError as e:
            logger.critical(e)
            self.running = False
        else:
            self.player = Player(self.buffer_request)
            logger.debug(f'{__name__} initiated')

    def _setup_logging(self):
        logging.basicConfig(
        level=FILE_LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding=LOG_ENCODING),
            console
            ])

    def run(self):
        if self.running:
            logger.info(f'Command-line Audio Decoding Engine with Navigation and Continuous Execution {version} started')

            Thread(target=self._listen, daemon=True).start()
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

    def buffer_request(self, request, connection=None):
        logger.info(f'Received request: {request} from {request.get('source', '[source not provided]')}')
        self.dispatch_buffer.put((request, connection))

    def _flush_buffer(self):
        while self.running:
            request, connection = self.dispatch_buffer.get()
            if request is SENTINELS.EXIT_FLUSHING:
                break
            try:
                response = self.dispatch(request)
            except Exception as e:
                logger.error(f'Failed to dispatch request: {e}')
                response = response_template.gen_dispatch_failed(e)

            if connection is not None:
                logger.info(f'Send response: {response}')
                send_json(connection, response)
                connection.close()

    def dispatch(self, request):
        response = {}
        action = request.get('action', None)
        cwd = request.get('cwd', None)
        if action is not None:
            keys_required = REQUIRED_KEYS.get(action, [])
            for key in keys_required:
                if key not in request.keys():
                    response = self._missing_key(action, key)
                    break
            else:

                # ----------------------------------------------------------------

                if action == 'status':
                    player_status = {
                        vlc.State.Playing: 'playing',
                        vlc.State.Paused: 'paused',
                        vlc.State.Stopped: 'stopped'
                    }.get(self.player.player.get_state(), 'unknown')

                    if self.current_song_info is None:
                        path = 'none'
                    else:
                        path = self.current_song_info[self.current_song_num]['path']
                    status = {
                        'path': path,
                        'in_library': self.current_song_in_lib,
                        'player_status': player_status,
                    }
                    progress = self.player.get_progress()
                    status['length'] = progress['length']
                    status['time'] = progress['time']
                    response = response_template.SUCCESS.copy()
                    response['attachment'] = status
                    
                elif action == 'open':
                    song = request['song']
                    id= self._get_song(song, cwd)
                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('open', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        self._set_current_song(self.database.get_song_info(id))
                        response = self.player.load_paths(self.current_song_info[0]['path'])
                    else:
                        path = Path(cwd) / song
                        info = self._get_playlist_songs(song)
                        if info is SENTINELS.PLAYLIST_EMPTY:
                            response = response_template.gen_playlist_empty(song)
                        elif info is not SENTINELS.PLAYLIST_NOT_FOUND:
                            self._set_current_song(info)
                            paths = list(map(lambda i: i['path'], info))
                            response = self.player.load_paths(paths)
                        else:
                            # Not in library, try to open as path
                            if path.is_file():
                                self._set_current_song([{'path': str(path)}], False)
                                response = self.player.load_paths(str(path))
                            else:
                                logger.warning(f'Can not open {path}')
                                response = response_template.gen_invalid_path(str(path))

                elif action == 'stop':
                    response = self.player.stop()

                elif action == 'pause':
                    response = self.player.pause()

                elif action == 'resume':
                    response = self.player.resume()

                elif action == 'toggle':
                    response = self.player.toggle()

                elif action == 'prev':
                    response = self.player.switch_prev()
                    self.current_song_num = self.player.number

                elif action == 'next':
                    response = self.player.switch_next()
                    self.current_song_num = self.player.number

                elif action == 'lib.list':
                    info = self.database.get_all_song_info()
                    if request.get('show_aliases', False):
                        for row in info:
                            aliases = self.database.get_song_aliases(row['id'])
                            row['aliases'] = aliases

                    response = response_template.SUCCESS.copy()
                    response['attachment'] = info

                elif action == 'lib.add':
                    path = request['path']
                    if Path(path).is_file():
                        ignored = self.database.add_song(path)[1]
                        if not ignored:
                            response = response_template.SUCCESS
                        else:
                            response = response_template.gen_song_exists(path)
                    else:
                        response = response_template.gen_invalid_path(path)

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
                        response = response_template.SUCCESS
                    else:
                        response = response_template.gen_song_not_exist(f'delete {song}')

                elif action == 'lib.reset':
                    self.database.reset()
                    if self.current_song_in_lib:
                        path = self.current_song_info[self.current_song_num]['path']
                        self._set_current_song({'path': path}, False)
                    response = response_template.SUCCESS

                elif action == 'lib.alias.list':
                    song = request['song']
                    id = self._get_song(song, cwd)
                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('lib.alias.list', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        aliases = self.database.get_song_aliases(id)
                        response = response_template.SUCCESS.copy()
                        response['attachment'] = aliases
                    else:
                        response = response_template.gen_song_not_exist(f'show aliases of {song}')

                elif action == 'lib.alias.bind':
                    song = request['song']
                    id = self._get_song(song, cwd)

                    if id is SENTINELS.MISSING_CWD:
                        response = self._missing_key('lib.alias.bind', 'cwd')
                    elif id is not SENTINELS.NOT_IN_LIB:
                        result = self.database.bind_alias(id, request['alias'])
                        response = {
                            SENTINELS.ALIAS_EXISTS: response_template.gen_alias_exists(request['alias']),
                            SENTINELS.DONE: response_template.SUCCESS,
                            SENTINELS.SONG_NOT_FOUND: response_template.gen_song_not_exist(f'bind alias to {song}') # not really necessary, but Monica insists
                        }[result]
                    else:
                        response = response_template.gen_song_not_exist(f'bind alias to {song}')

                elif action == 'lib.alias.unbind':
                    result = self.database.unbind_alias(request['alias'])
                    if result is not SENTINELS.ALIAS_NOT_FOUND:
                        response = response_template.SUCCESS
                    else:
                        response = response_template.gen_alias_not_exists(f'unbind {request["alias"]}')

                elif action == 'lib.playlist.list':
                    playlists = self.database.get_all_playlists()
                    response = response_template.SUCCESS.copy()
                    response['attachment'] = playlists

                elif action == 'lib.playlist.create':
                    name = request['name']
                    ignored = self.database.create_playlist(name)[1]
                    if not ignored:
                        response = response_template.SUCCESS
                    else:
                        response = response_template.gen_playlist_exists(name)

                elif action == 'lib.playlist.add':
                    playlist = self.database.get_playlist_via_name(request['playlist'])
                    if playlist is not SENTINELS.PLAYLIST_NOT_FOUND:
                        song = self._get_song(request['song'], cwd)
                        if song is SENTINELS.MISSING_CWD:
                            response = response_template.gen_missing_key('lib.playlist.add', 'cwd')
                        elif song is not SENTINELS.NOT_IN_LIB:
                            ignored = self.database.add_song_to_playlist(playlist, song)
                            if not ignored:
                                response = response_template.SUCCESS
                            else:
                                response = response_template.gen_playlist_song_exists(request['song'], request['playlist'])
                        else:
                            response = response_template.gen_song_not_exist(f'add song \"{request['song']}\" to playlist \"{request['playlist']}\"')
                    else:
                        response = response_template.gen_playlist_not_exist(request['playlist'])


                elif action == 'exit':
                    self.exit()
                    response = response_template.SUCCESS
                else:
                    logger.error(f'Invalid \"action\" value received: {action}')
                    response = response_template.INVALID_ACTION
        else:
            logger.error('Not \"action\" key found in request')
            response =  response_template.gen_missing_key('all', 'action')


        return response

    def _missing_key(self, action, key):
        logger.error(f'Missed key for action \"{action}\": \"{key}\"')
        return response_template.gen_missing_key(action, key)

    def _set_current_song(self, info, in_lib=True):
        if not isinstance(info, list):
            info = [info]
        self.current_song_info = info
        self.current_song_in_lib = in_lib
        self.current_song_num = 0
        logger.info(f'Set current info of current songs to {info}, in library {in_lib}')

    def _get_playlist_songs(self, name):
        playlist_id = self.database.get_playlist_via_name(name)
        if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
            ids = self.database.get_playlist_songs(playlist_id)
            if ids is not SENTINELS.PLAYLIST_EMPTY:
                info = self.database.get_song_info(ids)
                info = sorted(info, key=lambda x: Path(x['path']).name.lower())
                return info
            else:
                return SENTINELS.PLAYLIST_EMPTY
        else:
            return SENTINELS.PLAYLIST_NOT_FOUND
        

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

                logger.info(f'Received connection from {address}')
                Thread(target=self._handle_connection, args=(connection,), daemon=True).start()

    def _handle_connection(self, connection):
        request = recv_json(connection)
        if request is not None:
            self.buffer_request(request, connection)

    def exit(self, error=False, msg=None):
        if msg is not None:
            if error:
                logger.critical(msg)
                self.exit_code = 1
            else:
                logger.info(msg)
                self.exit_code = 0
        self.running = False

if __name__ == '__main__':
    Backend().run()
