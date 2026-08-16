from time import sleep

from src.log import setup_logger
from src.constants import HOTKEY_LOG_PATH
from src.constants import HEARTBEAT_POLL_INTERVAL
from src.client import test_heartbeat, confirm_dead

logger = setup_logger(__name__, HOTKEY_LOG_PATH)

class Hotkey:
    def __init__(self):
        self.running = True
        logger.debug('Hotkey frontend initialized')

    def run(self):
        logger.info('Started to listen hotkeys') # yep. It's definitely listening
        try:
            while self.running:
                sleep(HEARTBEAT_POLL_INTERVAL)
                code = test_heartbeat()
                if code == 4:
                    self.exit(force=True)
                elif code != 0:
                    self.exit()
        except KeyboardInterrupt:
            ...

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