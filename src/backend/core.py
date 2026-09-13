import sys
import os
import logging
from threading import Thread
import socket
import queue
import time

import vlc

from src import __version__
from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH, SILENT_LOG_LEVEL
from src.constants import (
    DATABASE_PATH, 
    DATABASE_DEV_PATH,
    BACKLOG, ACTION_KEYS, 
    NON_ACTION_KEYS, 
    IterType, 
    SERVER_TIMEOUT, 
    ACK,
    LOOP_INTERVAL, 
    PLAY_DEAD_TIME, 
    SOURCES, 
    READABLE_TYPE_NAMES
    )
from src.config import CONFIG
from src.sentinels import SENTINELS
from src.connection import recv_json, send_json
from src import gen_response
from src.backend.database.core import Database
from src.backend.vlc_player import Player
from src.backend.playback import Playback
from src.backend.context import Context
from src.backend.handlers import ROUTER
from src.pid import add_pid, remove_pid

logger = setup_logger(__name__, BACKEND_LOG_PATH)

class Backend:
    def __init__(self):
        self.pid = str(os.getpid())
        add_pid(self.pid)

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
        
        self.dispatch_buffer = queue.Queue() # single way
        self.notifies = []

        try:
            self.database = Database(database_path)
        except RuntimeError as e:
            logger.critical(e)
            self.running = False
        else:
            self.player = Player(self.buffer_request)
            self.playback = Playback(self.database)

            self.ctx = Context(
                database=self.database,
                player=self.player,
                playback=self.playback,
                exit_=self.exit_,
                start_time=time.time(),
                dev=self.dev
            )

            self.notifies.append(f'{CONFIG.username}, welcome to Command-line Audio Decoding Engine with Navigation and Continuous Execution') # just for fun

            if CONFIG.proxy != '':
                os.environ['HTTP_PROXY'] = CONFIG.proxy
                os.environ['HTTPS_PROXY'] = CONFIG.proxy

            logger.debug(f'HTTP proxy: {os.environ.get('HTTP_PROXY', '(empty)')}')
            logger.debug(f'HTTPS proxy: {os.environ.get('HTTPS_PROXY', '(empty)')}')

            if CONFIG.netease_skip_proxy:
                os.environ['NO_PROXY'] = ', '.join((os.environ.get('NO_PROXY', ''), '163.com'))

            logger.debug(f'Proxy whitelist: {os.environ.get('NO_PROXY', '(empty)')}')

            logger.debug(f'{__name__} initiated')

    def run(self):
        if self.running:
            logger.info(f'Command-line Audio Decoding Engine with Navigation and Continuous Execution {__version__} started, PID: {self.pid}')

            Thread(target=self._listen, daemon=True).start()
            Thread(target=self._memorize_pos, daemon=True).start()
            self._flush_thread = Thread(target=self._flush_buffer, daemon=True)
            self._flush_thread.start()

            if self.continue_last:
                self.buffer_request({'action': 'load_last', 'source': 'backend'})

            try:
                while self.running:
                    time.sleep(LOOP_INTERVAL)
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

            if not request.get('silent', False):
                log_request = request.copy()
                log_request['token'] = '*************'
                msg = f'Received request: {log_request} from {source}'
                if connection is not None:
                    msg += f' via socket connection from {address}'
                logger.info(msg)

            self.dispatch_buffer.put((request, connection))

    def _flush_buffer(self):
        while self.running:
            silent = False
            old_level = logger.level
            try:
                request, connection = self.dispatch_buffer.get()

                if request is SENTINELS.EXIT_FLUSHING:
                    break

                silent = request.get('silent', False)
                if silent:
                    old_level = logger.level
                    logger.setLevel(SILENT_LOG_LEVEL)
                    self.database.silence_on()

                try:
                    response = self.dispatch(request)
                except Exception as e:
                    logger.exception(f'Exception raised when dispatching request')
                    response = gen_response.Failed(f'a CADENCE backend error occurred during dispatching of request: \"{e}\"')



                if connection is not None and request.get('notify_support', False):
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

            finally:
                if silent:
                    logger.setLevel(old_level)
                    self.database.silence_off()

    def dispatch(self, request):
        response = gen_response.Undefined()
        request = self._process_request(request)
        if isinstance(request, gen_response.Response) and not request.ok():
            response = request
        else:
            action = request['action']

            handler = ROUTER.get(action, None)
            if handler is None:
                logger.error(f'Invalid \"action\" value received: {action}')
                response = gen_response.UnknownAction(action)
            else:
                response = handler(self.ctx, request)

        return response

    def _process_request(self, request) -> dict | gen_response.Response:
        if not isinstance(request, dict):
            return gen_response.Failed('request is not a dictionary')
        else:
            token = request.get('token', '')
            backend_token = CONFIG.backend_token
            if backend_token != '' and token != backend_token:
                return gen_response.AuthFailed()
            else:
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

    def _memorize_pos(self):
        while self.running:
            if self.playback.current_song_info is not None and self.player.player.get_state() == vlc.State.Playing:
                path = self.playback.get_playing_info()['path']
                pos = self.player.get_progress()['time']
                self.database.set_pos(path, pos, log=False)
            time.sleep(CONFIG.pos_memorize_interval)

    def _listen(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(SERVER_TIMEOUT)
        host = CONFIG.backend_host
        port = CONFIG.backend_port
        try:
            server.bind((host, port))
        except OSError as e:
            self.exit_(True, f'Failed to bind to {port}:{host}: {e}')
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
        if request is None:
            connection.close()
        else:
            send_json(connection, ACK)
            self.buffer_request(request, connection, address)

    def _play_dead(self): # give some time for daemon-like frontend to exit
        logger.info('Playing dead...')
        time.sleep(PLAY_DEAD_TIME)
        self.running = False

    def exit_(self, error=False, msg=None):
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
