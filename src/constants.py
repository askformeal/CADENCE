from platformdirs import PlatformDirs
from pathlib import Path
import logging

dirs = PlatformDirs('cadence', ensure_exists=True)

LOG_DIR = Path(dirs.user_log_dir)
LOG_PATH = LOG_DIR / 'cadence.log'

DATABASE_DIR = Path(dirs.user_data_dir)
DATABASE_PATH = DATABASE_DIR / 'cadence.db'

FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
LOG_ENCODING = 'utf-8'

MAIN_LOOP_INTERVAL = 0.05

HOST = '127.0.0.1'
PORT = 17891
TIMEOUT = 3
SERVER_TIMEOUT = 0.5
BACKLOG = 5
HEADER_LEN = 4
CONNECTION_ENCODING = 'utf-8'
MAX_JSON_SIZE = 10 * 1024 * 1024

PLAYER_TIMEOUT = 1
PLAYER_POLL_INTERVAL = 0.05

ACTION_KEYS = {
    'open': ['song'],
    'lib.add': ['path'],
    'lib.del': ['song'],
    'lib.alias.list': ['song'],
    'lib.alias.bind': ['song', 'alias'],
    'lib.alias.del': ['alias'],
}
