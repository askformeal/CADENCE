from platformdirs import PlatformDirs
from importlib.resources import files
from pathlib import Path
import logging

import readchar

from src.sentinels import SENTINELS
from src.converter import CONVERTER

class IterType:
    # can be list or tuple
    def __init__(self, element_type):
        self.element_type = element_type

ENCODING = 'utf-8'

# Paths
ICON_PATH = str(files('res') / 'icon.ico')
ERROR_ICON_PATH = str(files('res') / 'icon_error.ico')

dirs = PlatformDirs('cadence', ensure_exists=True)

DATA_DIR = Path(dirs.user_data_dir)

PID_PATH = DATA_DIR / 'PID.json'
CONFIG_PATH = DATA_DIR / 'config.toml'

LOG_DIR = Path(dirs.user_log_dir)
BACKEND_LOG_PATH = LOG_DIR / 'cadence.log'
SOCKET_LOG_PATH = LOG_DIR / 'cadence-socket.log'
HOTKEY_LOG_PATH = LOG_DIR / 'cadence-hotkey.log'
TRAY_LOG_PATH = LOG_DIR / 'cadence-tray.log'
DASH_LOG_PATH = LOG_DIR / 'cadence-dash.log'
CONFIG_LOG_PATH = LOG_DIR / 'cadence-config.log'
PID_LOG_PATH = LOG_DIR / 'cadence-pid.log'

DATABASE_PATH = DATA_DIR / 'cadence.db'
DATABASE_DEV_PATH = DATA_DIR / 'cadence-dev.db'

LOG_MAX_LENGTH = 500

FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
SILENT_LOG_LEVEL = logging.WARNING

# Time

TERMINATE_TIMEOUT = 3

LOOP_INTERVAL = 0.05
TRAY_POLL_INTERVAL = 0.5
DASH_POLL_INTERVAL = 0.1

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

HOTKEY_COOL_DOWN = 0.5

TRAY_ERROR_DISPLAY_TIME = 1.5

DASH_MAX_SHOW_SONG = 15
DASH_POS_BAR_LEN = 50
DASH_VOL_BAR_LEN = 20
DASH_TOAST_TIME = 3

MEDIA_KEY_TO_ACTION = {
    0xb0: 'next',
    0xb1: 'prev',
    0xb2: 'stop',
    0xb3: 'toggle',
}

READABLE_TYPE_NAMES = {
    str: 'string',
    int: 'integer',
    bool: 'boolean',
    IterType: 'list or tuple',
    CONVERTER.boolean: 'boolean',
    CONVERTER.port: 'network port',
    CONVERTER.pos_int: 'positive integer',
    CONVERTER.timeout: 'positive float',
    CONVERTER.percentage: 'percentage number'
}

BOX_STYLES = {
    'ascii': ('/', '\\', '\\', '/', '|', '='),
    'at': ('@', '@', '@', '@', '|', '='),
    'rounded': ('╭', '╮', '╰', '╯', '│', '─'),
    'square': ('┌', '┐', '└', '┘', '│', '─'),
    'double-corner': ('╔', '╗', '╚', '╝', '│', '─'),
    'heavy-corner': ('┏', '┓', '┗', '┛', '│', '─'),
    'double': ('╔', '╗', '╚', '╝', '║', '═'),
    'heavy': ('┏', '┓', '┗', '┛', '┃', '━'),
}

class DashKeyMap: # why not a dict? because this works better with my IDE's suggestions
    def __init__(self):
        self.toggle = readchar.key.SPACE
        self.stop = 'x'
        self.dice = 'd'

        self.forward = ('.', 'h', readchar.key.RIGHT)
        self.backward = (',', 'l', readchar.key.LEFT)

        self.shuffle = 's'
        self.loop = 'r'

        self.vol_up = '='
        self.vol_down = '-'
        self.mute = 'm'

        self.prev = 'p'
        self.next = 'n'

        self.select_up = ('k', readchar.key.UP)
        self.select_down = ('j', readchar.key.DOWN)
        self.select_current = 'c'

        self.page_up = readchar.key.PAGE_UP
        self.page_down = readchar.key.PAGE_DOWN

        self.switch_select = readchar.key.ENTER

        self.help = ('H', '?')

        self.next_box = 't'
        self.prev_box = 'T'

        self.redraw = (readchar.key.CTRL_L, readchar.key.F5)

        self.quit = ('q', readchar.key.CTRL_C, readchar.key.CTRL_Z)

        for name in vars(self).keys():
            value = getattr(self, name)
            if not isinstance(value, tuple):
                setattr(self, name, (value,))

DASH_KEY_MAP = DashKeyMap()

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
        'description': 'Username to show in the welcome message'
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
        'type': CONVERTER.timeout,
        'section': 'network',
        'default': 10,
        'description': 'Timeout of frontend-backend communication (seconds). May cause error if not enough higher than player timeout'
    },
    'hotkey': {
        'type': CONVERTER.boolean,
        'section': 'service',
        'default': True,
        'description': 'Whether to start hotkey service on start backend'
    },
    'tray': {
        'type': CONVERTER.boolean,
        'section': 'service',
        'default': True,
        'description': 'Whether to start system tray icon service on start backend'
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
        'type': CONVERTER.timeout,
        'section': 'playback',
        'default': 5,
        'description': 'Interval between update of the memorized position of the currently played song (seconds)'
    },
    'player_timeout': {
        'type': CONVERTER.timeout,
        'section': 'playback',
        'default': 1,
        'description': 'Timeout of backend waiting for a player action to be completed. May cause error if not enough lower than IPC timeout'
    },
    'dash_volume_step': {
        'type': CONVERTER.pos_int,
        'section': 'dash',
        'default': 5,
        'description': 'Step of volume increase/decrease on dashboard'
    },
    'dash_pos_step': {
        'type': CONVERTER.pos_int,
        'section': 'dash',
        'default': 5,
        'description': 'Step of position forward/backward on dashboard'
    },
    'cli_box_style': {
        'type': CONVERTER.box_style,
        'section': 'appearance',
        'default': 'rounded',
        'description': 'Box style of CLI'
    },
    'dash_box_style': {
        'type': CONVERTER.box_style,
        'section': 'appearance',
        'default': 'rounded',
        'description': 'Box style of dashboard'
    }
}

SOURCES = {
    SENTINELS.SOURCE_NOT_PROVIDED: '[source not provided]',
    'cli': 'teletypewriter interface (non-interactive)',
    'dash': 'teletypewriter interface (dashboard)',
    'backend': 'backend inter-process communication from backend',
    'player': 'backend inter-process communication from player',
    'hotkey': 'Hotkey control service',
    'tray': 'Tray icon control service',
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
    'token',
    'silent',
    'notify_support'
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
    'config.list',
    'config.show',
    'config.path'
]

METADATA = ['name', 'artist', 'album', 'duration', 'bitrate', 'sample_rate', 'channels']
SEARCH_META = ['name', 'artist', 'album'] # metadata that can be used for searching

FILE_META = {
    'title': 'name',
    'artist': 'artist',
    'album': 'album'
}

# file type descriptions, kept short like those used in file selectors
AUDIO_FILE_TYPES = (
    ('MP3 Audio', '.mp3'),
    ('FLAC Audio', '.flac'),
    ('WAV Audio', '.wav'),
    ('OGG Audio', '.ogg'),
    ('Opus Audio', '.opus'),
    ('OGG Audio', '.oga'),
    ('M4A Audio', '.m4a'),
    ('M4B Audio', '.m4b'),
    ('AAC Audio', '.aac'),
    ('MP4 Audio', '.mp4'),
    ('M4P Audio', '.m4p'),
    ('APE Audio', '.ape'),
    ('WMA Audio', '.wma'),
    ('AIFF Audio', '.aiff'),
    ('AIF Audio', '.aif'),
    ('AU Audio', '.au'),
    ('AC3 Audio', '.ac3'),
    ('DTS Audio', '.dts'),
    ('DSF Audio', '.dsf'),
    ('DSD Audio', '.dsd'),
    ('DFF Audio', '.dff'),
    ('MKA Audio', '.mka'),
    ('WV Audio', '.wv'),
    ('MPC Audio', '.mpc'),
    ('TTA Audio', '.tta'),
    ('TAK Audio', '.tak'),
    ('RA Audio', '.ra'),
    ('RM Audio', '.rm'),
    ('AMR Audio', '.amr'),
    ('3GP Audio', '.3gp'),
    ('CAF Audio', '.caf'),
    ('MIDI Audio', '.mid'),
    ('MIDI Audio', '.midi'),
    ('Speex Audio', '.spx'),
)

AUDIO_EXTENSIONS = set(map(lambda x: x[1], AUDIO_FILE_TYPES))

WINDOWS_ILLEGAL = r'[<>:"|?*]'
WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL',
                    'COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9',
                    'LPT1','LPT2','LPT3','LPT4','LPT5','LPT6','LPT7','LPT8','LPT9'}