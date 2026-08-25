import time
from threading import Thread

from pynput import keyboard

from src.log import setup_logger
from src.constants import HOTKEY_LOG_PATH
from src.constants import HEARTBEAT_POLL_INTERVAL, HOTKEY_COOL_DOWN, MEDIA_KEY_TO_ACTION
from src.client import test_heartbeat, confirm_dead, send_request

logger = setup_logger(__name__, HOTKEY_LOG_PATH)

class Hotkey:
    def __init__(self):
        self.running = True
        self.cool_down = {}
        logger.debug('Hotkey frontend initialized')

    def run(self):
        Thread(target=self._listen, daemon=True).start()
        try:
            while self.running:
                time.sleep(HEARTBEAT_POLL_INTERVAL)
                code = test_heartbeat()
                self._handle_code(code)
                
        except KeyboardInterrupt:
            ...

    def _handle_code(self, code):
        if code == 4:
            self.exit(force=True)
        elif code != 0:
            self.exit()

    def _get_vk(self, key):
        return getattr(getattr(key, 'value', key), 'vk', None)

    def _on_press(self, key):
        try:
            vk = self._get_vk(key)
            if vk in MEDIA_KEY_TO_ACTION.keys():
                last_press_time = self.cool_down.get(vk, 0)

                if (time.time() - last_press_time) > HOTKEY_COOL_DOWN:
                    self.cool_down[vk] = time.time()
                    action = MEDIA_KEY_TO_ACTION[vk]
                    logger.info(f'action triggered: {action}')
                    response = send_request(action=action, source='hotkey')
                    self._handle_code(response['code'])
        except Exception as e:
            logger.exception('An error occurred during handling a key press')

    def _on_release(self, key):
        vk = self._get_vk(key)
        if vk in MEDIA_KEY_TO_ACTION.keys():
            self.cool_down[vk] = 0

    def _listen(self):
        logger.info('Started to listen hotkeys') # yep. It's definitely listening
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as listener:
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