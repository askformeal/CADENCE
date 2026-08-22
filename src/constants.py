from platformdirs import PlatformDirs
from pathlib import Path
import logging

from src.sentinels import SENTINELS

class IterType:
    # can be list or tuple
    def __init__(self, element_type):
        self.element_type = element_type

dirs = PlatformDirs('cadence', ensure_exists=True)

LOG_DIR = Path(dirs.user_log_dir)
BACKEND_LOG_PATH = LOG_DIR / 'cadence.log'
SOCKET_LOG_PATH = LOG_DIR / 'cadence-socket.log'
HOTKEY_LOG_PATH = LOG_DIR / 'cadence-hotkey.log'

DATABASE_DIR = Path(dirs.user_data_dir)
DATABASE_PATH = DATABASE_DIR / 'cadence.db'
DATABASE_DEV_PATH = DATABASE_DIR / 'cadence-dev.db'

FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
LOG_ENCODING = 'utf-8'

MAIN_LOOP_INTERVAL = 0.05

HEARTBEAT_POLL_INTERVAL = 3
DEATH_CONFIRM_INTERVAL = 0.3
DEATH_CONFIRM_NUMBER = 10
PLAY_DEAD_TIME = 5

HOST = '127.0.0.1'
PORT = 17891
TIMEOUT = 10

STARTER_CHECK_INTERVAL = 0.5
STARTER_RETRY = 5

RESTART_NUM = 15
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
    'backend': 'backend inter-process communication from backend',
    'player': 'backend inter-process communication from player',
    'hotkey': 'Hotkey control service',
    'alive': 'alive test',
    'heartbeat': 'heartbeat test',
}

# 'key name': (type, is_required)
# literal type: (IterType(element_type), is_required). every element needs to match
ACTION_KEYS = {
    'open': {
        'song': (str, True)
    },
    'switch': {
        'number': (int, True)
    },
    'seek': {
        'time': (str, True)
    },
    'jump': {
        'progress': (int, True)
    },
    'volume': {
        'volume': (int, True)
    },
    'lib.info':
    {
        'songs': (IterType(str), True),
        'show_aliases': (bool, False),
        'show_playlists': (bool, False)
    },
    'lib.list': {
        'show_aliases': (bool, False),
        'show_playlists': (bool, False),
        'show_tech': (bool, False)
    },
    'lib.search': {
        'keyword': (IterType(str), True),
        'or': (bool, False)
    },
    'lib.add': {
        'paths': (IterType(str), True),
        'aliases': (IterType(str), False),
        'skip_meta': (bool, False),
        'skip_alias': (bool, False)
    },
    'lib.del': {
        'song': (str, True)
    },
    'lib.prune':
    {
        'dry_run': (bool, False),
    },
    'lib.scan': {
        'dir': (str, True),
        'playlist': (str, False),
        'recurse': (bool, False),
        'dry_run': (bool, False),
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
        'playlist': (str, False),
        'show_aliases': (bool, False),
        'show_playlists': (bool, False),
        'show_tech': (bool, False)
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
    bool: 'boolean',
    IterType: 'list or tuple'
}

ATTACHMENT_REQUIRED_ACTIONS = [
    'status',
    'list',
    'lib.info',
    'lib.list',
    'lib.search',
    'lib.prune',
    'lib.scan',
    'lib.alias.list',
    'lib.playlist.list',
]

METADATA = ['name', 'artist', 'album', 'duration', 'bitrate', 'sample_rate', 'channels']
SEARCH_META = ['name', 'artist', 'album'] # metadata that can be used for searching

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