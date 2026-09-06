import sqlite3
import threading

from .logger import logger
from src.constants import SILENT_LOG_LEVEL
from .misc import MiscMixin
from .song import SongMixin
from .alias import AliasMixin
from .playlist import PlaylistMixin
from .position import PosMixin
from .settings import SettingsMixin


class Database(MiscMixin, SongMixin, AliasMixin, PlaylistMixin, PosMixin, SettingsMixin):
    def __init__(self, database_path):
        self.old_level = logger.level
        self._lock = threading.Lock()

        try:
            self.connection = sqlite3.connect(database_path, check_same_thread=False, isolation_level=None)
        except sqlite3.Error as e:
            raise RuntimeError(f'Failed to connect to database: {e}') from e
        else:
            self.connection.execute("PRAGMA journal_mode = WAL").fetchone()
            self.connection.row_factory = sqlite3.Row

            self.cursor = self.connection.cursor()
            self._init_database()
            logger.debug(f'{__name__} initiated')

    def silence_on(self):
        self.old_level = logger.level
        logger.setLevel(SILENT_LOG_LEVEL)

    def silence_off(self):
        logger.setLevel(self.old_level)
        
    def execute(self, sql, *parameters):
        parameters = tuple(parameters)

        if not sql.strip():
            raise ValueError('Empty SQL statement')
        else:
            with self._lock:
                return self.cursor.execute(sql, parameters)

    def on_exit(self):
        self.connection.commit()
        self.connection.close()