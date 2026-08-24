from platformdirs import PlatformDirs
from pathlib import Path
import logging

from src.sentinels import SENTINELS
from src.converter import CONVERTER

class IterType:
    # can be list or tuple
    def __init__(self, element_type):
        self.element_type = element_type

ENCODING = 'utf-8'

# Paths

dirs = PlatformDirs('cadence', ensure_exists=True)

DATA_DIR = Path(dirs.user_data_dir)

PID_PATH = DATA_DIR / 'PID.json'
CONFIG_PATH = DATA_DIR / 'config.toml'

LOG_DIR = Path(dirs.user_log_dir)
BACKEND_LOG_PATH = LOG_DIR / 'cadence.log'
SOCKET_LOG_PATH = LOG_DIR / 'cadence-socket.log'
HOTKEY_LOG_PATH = LOG_DIR / 'cadence-hotkey.log'
CONFIG_LOG_PATH = LOG_DIR / 'cadence-config.log'
PID_LOG_PATH = LOG_DIR / 'cadence-pid.log'

DATABASE_PATH = DATA_DIR / 'cadence.db'
DATABASE_DEV_PATH = DATA_DIR / 'cadence-dev.db'

FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO

# Time

TERMINATE_TIMEOUT = 3

MAIN_LOOP_INTERVAL = 0.05

HEARTBEAT_POLL_INTERVAL = 3
DEATH_CONFIRM_INTERVAL = 0.3
DEATH_CONFIRM_NUMBER = 10
PLAY_DEAD_TIME = 5

STARTER_CHECK_INTERVAL = 0.5
STARTER_RETRY = 5

RESTART_NUM = 15
RESTART_POLL_INTERVAL = 0.5

SERVER_TIMEOUT = 0.5
BACKLOG = 5
HEADER_LEN = 4
CONNECTION_ENCODING = 'utf-8'
MAX_JSON_SIZE = 10 * 1024 * 1024

PLAYER_POLL_INTERVAL = 0.05

MIN_TIMEOUT = 0.01

READABLE_TYPE_NAMES = {
    str: 'string',
    int: 'integer',
    bool: 'boolean',
    IterType: 'list or tuple',
    CONVERTER.boolean: 'boolean',
    CONVERTER.port: 'network port',
    CONVERTER.pos_float: 'positive float',
    CONVERTER.percentage: 'percentage number'
}

# Config

# dunno if scheme is the right name
# each option name must be unique
# "type" will be called to convert the value. raise ValueError if invalid
# default value will not go through type converter. make sure they are valid
CONFIG_SCHEME = {
    'username': {
        'type': str,
        'section': SENTINELS.ROOT_SECTION,
        'default': 'J. Doe',
        'description': 'Name to show in the welcome message'
    },
    'backend_token': {
        'type': str,
        'section': 'network',
        'default': '',
        'description': 'Token for backend to verify requests with. Empty means authentication is disabled'
    },
    'frontend_token': {
        'type': str,
        'section': 'network',
        'default': '',
        'description': 'Token for frontend to send with'
    },
    'backend_port': { 
        'type': CONVERTER.port,
        'section': 'network',
        'default': 17891, 
        'description': 'Port for backend to listen on'
    },
    'backend_host': {
        'type': str,
        'section': 'network',
        'default': '127.0.0.1',
        'description': 'Host for backend to listen on'
    },
    'frontend_port': { 
        'type': CONVERTER.port,
        'section': 'network',
        'default': 17891, 
        'description': 'Port for frontend to send requests to'
    },
    'frontend_host': {
        'type': str,
        'section': 'network',
        'default': '127.0.0.1',
        'description': 'Host for frontend to send requests to'
    },
    'ipc_timeout': {
        'type': CONVERTER.pos_float,
        'section': 'network',
        'default': 10,
        'description': 'Timeout of frontend-backend communication (seconds). May cause error if not enough higher than player timeout'
    },
    'default_volume': {
        'type': CONVERTER.percentage,
        'section': 'playback',
        'default': 100,
        'description': 'Volume on start (0~100)'
    },
    'default_shuffle': {
        'type': CONVERTER.boolean,
        'section': 'playback',
        'default': False,
        'description': 'Shuffle mode on start'
    },
    'pos_memorize_interval': {
        'type': CONVERTER.pos_float,
        'section': 'playback',
        'default': 5,
        'description': 'Interval between update of the memorized position of the currently played song (seconds)'
    },
    'player_timeout': {
        'type': CONVERTER.pos_float,
        'section': 'playback',
        'default': 1,
        'description': 'Timeout of backend waiting for a player action to be completed. May cause error if not enough lower than IPC timeout'
    }
}

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

    'lib.meta.read-file': {
        'song': (str, True),
        'name': (bool, False, False),
        'artist': (bool, False, False),
        'album': (bool, False, False),
        'duration': (bool, False, False),
        'bitrate': (bool, False, False),
        'sample_rate': (bool, False, False),
        'channels': (bool, False, False),
        'all': (bool, False, False),
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
    'config.show': {
        'option': (str, True)
    },
    'config.set': {
        'option': (str, True),
        'value': (str, True),
        'overwrite_corrupt': (bool, False, False)
    },
    'config.unset': {
        'option': (str, True)
    },
}

NON_ACTION_KEYS = {
    'action',
    'cwd',
    'source',
    'token'
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
    'config.show',
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