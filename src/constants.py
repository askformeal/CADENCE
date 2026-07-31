from platformdirs import PlatformDirs
from pathlib import Path
import logging

class _ConnectionLost:
    def __repr__(self):
        return 'Connection Lost'

# sentinel
LOST = _ConnectionLost()

dirs = PlatformDirs('cadence', ensure_exists=True)

LOG_DIR = Path(dirs.user_log_dir)
LOG_PATH = LOG_DIR / 'cadence.log'

FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
LOG_ENCODING = 'utf-8'

HOST = '127.0.0.1'
PORT = 17891
TIMEOUT = 3
BACKLOG = 5
HEADER_LEN = 4
CONNECTION_ENCODING = 'utf-8'
MAX_JSON_SIZE = 10 * 1024 * 1024

PLAYER_TIMEOUT = 1
PLAYER_POLL_INTERVAL = 0.05

ACTION_KEYS = {
    'open': ['path']
}