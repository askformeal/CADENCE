import time
from threading import Thread

from pynput import keyboard

from src.log import setup_logger
from src.constants import HOTKEY_LOG_PATH
from src.constants import HEARTBEAT_POLL_INTERVAL, HOTKEY_COOL_DOWN, MEDIA_KEY_TO_ACTION
from src.client import test_heartbeat, send_request, handle_code

logger = setup_logger(__name__, HOTKEY_LOG_PATH)

class Hotkey:
    def __init__(self):
        self.running = True
        self.cool_down = {}
        logger.debug(f'{__name__} initiated')

    def run(self):
        Thread(target=self._listen, daemon=True).start()
        try:
            while self.running:
                time.sleep(HEARTBEAT_POLL_INTERVAL)
                code = test_heartbeat()
                handle_code(code, self.exit)
                
        except KeyboardInterrupt:
            ...

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
                    response = send_request(action=action, source='hotkey', notify_support=False)
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

    def exit(self): # I might need it. What did I say.
        logger.info('Exit hotkey frontend')
        self.running = False

if __name__ == '__main__':
    Hotkey().run()