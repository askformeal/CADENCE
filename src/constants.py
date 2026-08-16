from platformdirs import PlatformDirs
from pathlib import Path
import logging

from src.sentinels import SENTINELS

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

RESTART_NUM = 3
RESTART_POLL_INTERVAL = 0.5

SERVER_TIMEOUT = 0.5
BACKLOG = 5
HEADER_LEN = 4
CONNECTION_ENCODING = 'utf-8'
MAX_JSON_SIZE = 10 * 1024 * 1024

PLAYER_TIMEOUT = 1
PLAYER_POLL_INTERVAL = 0.05
POS_MEMORIZE_INTERVAL = 5

SOURCES = {
    SENTINELS.SOURCE_NOT_PROVIDED: '[source not provided]',
    'cli': 'teletypewriter interface (non-interactive)',
    'player': 'backend inter-process communication from player'
}

# 'key name': (type, is_required)
ACTION_KEYS = {
    'open': {
        'song': (str, True)
    },
    'switch': {
        'number': (int, True)
    },
    'jump': {
        'progress': (int, True)
    },
    'lib.list': {
        'show_aliases': (bool, False)
    },
    'lib.add': {
        'path': (str, True),
        'alias': (str, False),
        'skip_meta': (bool, False),
        'skip_alias': (bool, False)
    },
    'lib.del': {
        'song': (str, True)
    },
    'lib.scan': {
        'dir': (str, True),
        'playlist': (str, False),
        'recurse': (bool, False),
        'preview': (bool, False),
        'skip_meta': (bool, False),
        'skip_alias': (bool, False)
    },
    'lib.meta.set': {
        'song': (str, True),
        'name': (str, False),
        'artist': (str, False),
        'album': (str, False)
    },
    'lib.alias.list': {
        'song': (str, True)
    },
    'lib.alias.bind': {
        'song': (str, True),
        'alias': (str, True)
    },
    'lib.alias.unbind': {
        'alias': (str, True)
    },
    'lib.playlist.list': {
        'playlist': (str, False)
    },
    'lib.playlist.create': {
        'name': (str, True)
    },
    'lib.playlist.add': {
        'song': (str, True),
        'playlist': (str, True)
    },
    'lib.playlist.kick': {
        'song': (str, True),
        'playlist': (str, True),
    },
    'lib.playlist.del': {
        'playlist': (str, True)
    },
}

READABLE_TYPE_NAMES = {
    str: 'string',
    int: 'integer',
    bool: 'boolean'
}

ATTACHMENT_REQUIRED_ACTIONS = [
    'status',
    'list',
    'lib.list',
    'lib.scan',
    'lib.alias.list',
    'lib.playlist.list',
]

METADATA = ['name', 'artist', 'album']
FILE_META = {
    'title': 'name',
    'artist': 'artist',
    'album': 'album'
}

AUDIO_EXTENSIONS = {
    '.mp3', '.flac', '.wav', '.ogg', '.opus', '.oga',
    '.m4a', '.m4b', '.aac', '.mp4', '.m4p',
    '.ape', '.wma', '.aiff', '.aif', '.au',
    '.ac3', '.dts', '.dsf', '.dsd', '.dff',
    '.mka', '.wv', '.mpc', '.tta', '.tak',
    '.ra', '.rm', '.amr', '.3gp', '.caf',
    '.mid', '.midi', '.spx',
}