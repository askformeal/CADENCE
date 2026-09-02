from src.types import IterType
from src.sentinels import SENTINELS

HEARTBEAT_POLL_INTERVAL = 3
DEATH_CONFIRM_INTERVAL = 0.3
DEATH_CONFIRM_NUMBER = 10

SERVER_TIMEOUT = 0.5
BACKLOG = 5
HEADER_LEN = 4
CONNECTION_ENCODING = 'utf-8'
MAX_JSON_SIZE = 10 * 1024 * 1024

SOURCES = {
    SENTINELS.SOURCE_NOT_PROVIDED: '[source not provided]',
    'cli': 'teletypewriter interface (non-interactive)',
    'dash': 'teletypewriter interface (dashboard)',
    'backend': 'backend inter-process communication from backend',
    'player': 'backend inter-process communication from player',
    'hotkey': 'Hotkey control service',
    'tray': 'Tray icon control service',
    'lyric': 'lyric board service service',
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
        'volume': (str, True)
    },
    'lib.info':
    {
        'songs': (IterType(str), True),
        'show_aliases': (bool, False, False),
        'show_playlists': (bool, False, False),
        'force_id': (bool, False, False)
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
        'skip_lyric': (bool, False, False),
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
        'skip_alias': (bool, False, False),
        'skip_lyric': (bool, False, False),
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
        'lyric': (str, False, None),
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
    'lib.lyric.set':
    {
        'song': (str, True),
        'path': (str, True)
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