import sys
import logging
from threading import Thread
import socket
import queue
from time import sleep

from src import version
from src.constants import LOG_PATH, FILE_LOG_LEVEL, CONSOLE_LOG_LEVEL, LOG_ENCODING
from src.constants import HOST, PORT, BACKLOG, ACTION_KEYS, SERVER_TIMEOUT
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
        self._setup_logging()
        self.running = True
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

            while self.running:
                sleep(MAIN_LOOP_INTERVAL)

            logger.info('Exit')
            self.dispatch_buffer.put((SENTINELS.EXIT_FLUSHING, SENTINELS.EXIT_FLUSHING))
            self._flush_thread.join()
            self.database.on_exit()
            self.player.on_exit()
            logging.shutdown()
            sys.exit(0)

        else:
            sys.exit(1)
            
    def exit(self, error=False, error_msg=None):
        if error_msg is not None:
            if error:
                logger.critical(error_msg)
            else:
                logger.info(error_msg)
        self.running = False

    def buffer_request(self, request, connection=None):
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
                send_json(connection, response)
                connection.close()

    def dispatch(self, request):
        response = {}
        action = request.get('action', None)
        if action is not None:
            keys_required = ACTION_KEYS.get(action, [])
            for key in keys_required:
                if key not in request.keys():
                    logger.error(f'Missed key for action \"{action}\": \"{key}\"')
                    response = response_template.gen_missing_key(action, key)
                    break
            else:
                if action == 'open':
                    response = self.player.load_paths([request['path']])
                elif action == 'pause':
                    response = self.player.pause()
                elif action == 'next':
                    response = self.player.switch_next()
                elif action == 'exit':
                    self.exit()
                    response = response_template.SUCCESS
                else:
                    logger.error(f'Invalid \"action\" value received: {action}')
                    response = response_template.INVALID_ACTION
        else:
            logger.error('Not \"action\" key found in request')
            response =  response_template.MISSING_ACTION

        return response

    def _listen(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.settimeout(SERVER_TIMEOUT)
        server.bind((HOST, PORT))
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
            logger.info(f'Received request: {request}')
            self.buffer_request(request, connection)

if __name__ == '__main__':
    Backend().run()