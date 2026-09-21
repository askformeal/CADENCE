from platformdirs import PlatformDirs
from importlib.resources import files
from pathlib import Path

ICON_PATH = str(files('res') / 'icon.ico')
ERROR_ICON_PATH = str(files('res') / 'icon_error.ico')
LYRIC_ICON_PATH = str(files('res') / 'lyric_icon.ico')
NO_COVER_PATH = str(files('res') / 'no_cover.txt')
REMOTE_ICON_PATH = str(files('res') / 'remote.png')
REFRESH_ICON_PATH = str(files('res') / 'refresh.png')
EDIT_ICON_PATH = str(files('res') / 'edit.png')

dirs = PlatformDirs('cascade', ensure_exists=True)

DATA_DIR = Path(dirs.user_data_dir)

PID_PATH = DATA_DIR / 'PID.json'
CONFIG_PATH = DATA_DIR / 'config.toml'

LOG_DIR = Path(dirs.user_log_dir)
BACKEND_LOG_PATH = LOG_DIR / 'cascade.log'
SOCKET_LOG_PATH = LOG_DIR / 'cascade-socket.log'
HOTKEY_LOG_PATH = LOG_DIR / 'cascade-hotkey.log'
TRAY_LOG_PATH = LOG_DIR / 'cascade-tray.log'
LYRIC_LOG_PATH = LOG_DIR / 'cascade-lyric.log'
DASH_LOG_PATH = LOG_DIR / 'cascade-dash.log'
CONFIG_GUI_LOG_PATH = LOG_DIR / 'cascade-config-gui.log'
CONFIG_LOG_PATH = LOG_DIR / 'cascade-config.log'
PID_LOG_PATH = LOG_DIR / 'cascade-pid.log'
UTIL_LOG_PATH = LOG_DIR / 'cascade-util.log'

DATABASE_PATH = DATA_DIR / 'cascade.db'
DATABASE_DEV_PATH = DATA_DIR / 'cascade-dev.db'