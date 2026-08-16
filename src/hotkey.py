from time import sleep
from threading import Thread

from pynput import keyboard

from src.log import setup_logger
from src.constants import HOTKEY_LOG_PATH
from src.constants import HEARTBEAT_POLL_INTERVAL
from src.client import test_heartbeat, confirm_dead, send_request

logger = setup_logger(__name__, HOTKEY_LOG_PATH)

class Hotkey:
    def __init__(self):
        self.running = True
        logger.debug('Hotkey frontend initialized')

    def run(self):
        Thread(target=self._listen, daemon=True).start()
        try:
            while self.running:
                sleep(HEARTBEAT_POLL_INTERVAL)
                code = test_heartbeat()
                self._handle_code(code)
                
        except KeyboardInterrupt:
            ...

    def _handle_code(self, code):
        if code == 4:
            self.exit(force=True)
        elif code != 0:
            self.exit()

    def _on_release(self, key):
        action = None
        if key == keyboard.Key.media_next:
            action = 'next'
        elif key == keyboard.Key.media_previous:
            action = 'prev'
        elif key == keyboard.Key.media_stop:
            action = 'stop'
        elif key == keyboard.Key.media_play_pause:
            action = 'toggle'

        if action is not None:
            logger.info(f'action triggered: {action}')
            response = send_request(action=action, source='hotkey')
            self._handle_code(response['code'])

    def _listen(self):
        logger.info('Started to listen hotkeys') # yep. It's definitely listening
        with keyboard.Listener(on_release=self._on_release) as listener:
            listener.join()

    def exit(self, force=False): # I might need it. What did I say.
        if force:
            self.running = False
            logger.info('Forcefully exit hotkey frontend')
        else:
            logger.info('Backend heartbeat died, confirming...')
            if confirm_dead():
                logger.info('Death confirmed. Exit hotkey frontend')
                self.running = False
            else:
                logger.info('Heartbeat resumed')

if __name__ == '__main__':
    Hotkey().run()