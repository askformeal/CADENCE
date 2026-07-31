import logging
from threading import Thread
import socket
import queue

from src import version
from src.constants import LOG_PATH, FILE_LOG_LEVEL, CONSOLE_LOG_LEVEL, LOG_ENCODING
from src.constants import HOST, PORT, BACKLOG, ACTION_KEYS
from src.connection import recv_json, send_json
from src.response import response_template
from src.player import Player

console = logging.StreamHandler()
console.setLevel(CONSOLE_LOG_LEVEL)

logging.basicConfig(
    level=FILE_LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding=LOG_ENCODING),
        console
    ]
)

class Backend:
    def __init__(self):
        self.running = True
        self.dispatch_buffer = queue.Queue() # single way
        self.player = Player(self.buffer_request)
        logging.debug(f'{__name__} initiated')

    def run(self):
        logging.info(f'Command-line Audio Decoding Engine with Navigation and Continuous Execution {version} started')
        Thread(target=self._listen, daemon=True).start()
        Thread(target=self._flush_buffer, daemon=True).start()
        while self.running:
            ...
        logging.info('Exit')
            
    def exit(self):
        self.running = False

    def buffer_request(self, request, connection=None):
        self.dispatch_buffer.put((request, connection))

    def _flush_buffer(self):
        while self.running:
            request, connection = self.dispatch_buffer.get()
            try:
                response = self.dispatch(request)
            except Exception as e:
                logging.error(f'Failed to dispatch request: {e}')
                response = response_template.gen_dispatch_failed(e)

            if connection is not None:
                send_json(connection, response)

    def dispatch(self, request):
        response = {}
        action = request.get('action', None)
        if action is not None:
            keys_required = ACTION_KEYS.get(action, [])
            for key in keys_required:
                if key not in request.keys():
                    logging.error(f'Missed key for action \"{action}\": \"{key}\"')
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
                    logging.error(f'Invalid \"action\" value received: {action}')
                    response = response_template.INVALID_ACTION
        else:
            logging.error('Not \"action\" key found in request')
            response =  response_template.MISSING_ACTION

        return response

    def _listen(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen(BACKLOG)
        logging.info(f'started listening on {HOST}:{PORT}')
        while self.running:
            connection, address = server.accept()
            logging.info(f'Received connection from {address}')
            Thread(target=self._handle_connection, args=(connection,)).start()

    def _handle_connection(self, connection):
        request = recv_json(connection)
        if request is not None:
            logging.info(f'Received request: {request}')
            self.buffer_request(request, connection)

if __name__ == '__main__':
    Backend().run()