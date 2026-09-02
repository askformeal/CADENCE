from platformdirs import PlatformDirs
from importlib.resources import files
from pathlib import Path

ICON_PATH = str(files('res') / 'icon.ico')
ERROR_ICON_PATH = str(files('res') / 'icon_error.ico')
LYRIC_ICON_PATH = str(files('res') / 'lyric_icon.ico')

dirs = PlatformDirs('cadence', ensure_exists=True)

DATA_DIR = Path(dirs.user_data_dir)

PID_PATH = DATA_DIR / 'PID.json'
CONFIG_PATH = DATA_DIR / 'config.toml'

LOG_DIR = Path(dirs.user_log_dir)
BACKEND_LOG_PATH = LOG_DIR / 'cadence.log'
SOCKET_LOG_PATH = LOG_DIR / 'cadence-socket.log'
HOTKEY_LOG_PATH = LOG_DIR / 'cadence-hotkey.log'
TRAY_LOG_PATH = LOG_DIR / 'cadence-tray.log'
LYRIC_LOG_PATH = LOG_DIR / 'cadence-lyric.log'
DASH_LOG_PATH = LOG_DIR / 'cadence-dash.log'
CONFIG_LOG_PATH = LOG_DIR / 'cadence-config.log'
PID_LOG_PATH = LOG_DIR / 'cadence-pid.log'

DATABASE_PATH = DATA_DIR / 'cadence.db'
DATABASE_DEV_PATH = DATA_DIR / 'cadence-dev.db'