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

# 'key name': (type, is_required, default_value)
# literal type: (IterType(element_type), is_required). every element needs to match
ACTION_KEYS = {
    'open': {
        'song': (str, True)
    },
    'switch': {
        'number': (int, True)
    },
    'next': {
        'on_end': (bool, False, False)
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
        'show_aliases': (bool, False, False),
        'show_playlists': (bool, False, False)
    },
    'lib.list': {
        'show_aliases': (bool, False, False),
        'show_playlists': (bool, False, False),
        'show_tech': (bool, False, False)
    },
    'lib.search': {
        'keyword': (IterType(str), True),
        'or': (bool, False, False)
    },
    'lib.add': {
        'paths': (IterType(str), True),
        'aliases': (IterType(str), False, []),
        'skip_meta': (bool, False, False),
        'skip_alias': (bool, False, False),
        'loose_path': (bool, False, False)
    },
    'lib.del': {
        'songs': (IterType(str), True)
    },
    'lib.prune':
    {
        'dry_run': (bool, False, False),
    },
    'lib.scan': {
        'dir': (str, True),
        'playlist': (str, False, None),
        'recurse': (bool, False, False),
        'dry_run': (bool, False, False),
        'skip_meta': (bool, False, False),
        'skip_alias': (bool, False, False)
    },
    'lib.meta.set': {
        'song': (str, True),
        'name': (str, False, None),
        'artist': (str, False, None),
        'album': (str, False, None),
        'duration': (int, False, None),
        'bitrate': (int, False, None),
        'sample_rate': (int, False, None),
        'channels': (int, False, None),
    },
    'lib.alias.list': {
        'song': (str, True)
    },
    'lib.alias.bind': {
        'song': (str, True),
        'aliases': (IterType(str), True)
    },
    'lib.alias.unbind': {
        'aliases': (IterType(str), True)
    },
    'lib.playlist.list': {
        'playlist': (str, False, None),
        'show_aliases': (bool, False, False),
        'show_playlists': (bool, False, False),
        'show_tech': (bool, False, False)
    },
    'lib.playlist.create': {
        'name': (str, True)
    },
    'lib.playlist.add': {
        'playlist': (str, True),
        'songs': (IterType(str), True)
    },
    'lib.playlist.kick': {
        'playlist': (str, True),
        'songs': (IterType(str), True)
    },
    'lib.playlist.del': {
        'playlist': (str, True)
    },
}

NON_ACTION_KEYS = {
    'action',
    'cwd',
    'source'
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

WINDOWS_ILLEGAL = r'[<>:"|?*]'
WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL',
                    'COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9',
                    'LPT1','LPT2','LPT3','LPT4','LPT5','LPT6','LPT7','LPT8','LPT9'}