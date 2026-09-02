from src.sentinels import SENTINELS
from src.types import CONVERTER

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
    },
    'dash_screen_buffer': {
        'type': CONVERTER.boolean,
        'section': 'appearance',
        'default': True,
        'description': 'Whether to use alt screen buffer for dashboard'
    },
    'auto_dash_height': {
        'type': CONVERTER.boolean,
        'section': 'appearance',
        'default': True,
        'description': 'Whether to automatically set dashboard height depending on terminal height'
    }
}