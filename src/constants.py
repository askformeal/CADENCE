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
STARTER_CHECK_INTERVAL = 0.5
STARTER_RETRY = 5
SERVER_TIMEOUT = 0.5
BACKLOG = 5
HEADER_LEN = 4
CONNECTION_ENCODING = 'utf-8'
MAX_JSON_SIZE = 10 * 1024 * 1024

PLAYER_TIMEOUT = 1
PLAYER_POLL_INTERVAL = 0.05
POS_MEMORIZE_INTERVAL = 5

REQUIRED_KEYS = {
    'open': ['song'],
    'switch': ['number'],
    'lib.add': ['path'],
    'lib.del': ['song'],
    'lib.meta.set': ['song'],
    'lib.alias.list': ['song'],
    'lib.alias.bind': ['song', 'alias'],
    'lib.alias.unbind': ['alias'],
    'lib.playlist.create': ['name'],
    'lib.playlist.add': ['song', 'playlist'],
    'lib.playlist.kick': ['song', 'playlist'],
    'lib.playlist.del': ['playlist'],
}

METADATA = ['name', 'artist', 'album']

AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.ogg', '.opus', '.oga',
    '.m4a', '.m4b', '.aac', '.mp4', '.m4p',
    '.ape', '.wma', '.aiff', '.aif', '.au',
    '.ac3', '.dts', '.dsf', '.dsd', '.dff',
    '.mka', '.wv', '.mpc', '.tta', '.tak',
    '.ra', '.rm', '.amr', '.3gp', '.caf',
    '.mid', '.midi', '.spx',
}