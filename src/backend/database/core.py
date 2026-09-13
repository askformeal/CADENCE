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
        self.database_path = database_path
        self.old_level = logger.level
        self._local = threading.local()
        self._get_connection()
        self._init_database()
        logger.debug(f'{__name__} initiated')

    def _new_connection(self):
        connection = sqlite3.connect(self.database_path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL").fetchone()
        connection.execute('PRAGMA foreign_keys = ON')
        logger.debug(f'New connection opened for thread \"{threading.get_ident()}\"')
        return connection

    def _get_connection(self):
        connection = getattr(self._local, 'connection', None)
        if connection is None:
            connection = self._new_connection()
            self._local.connection = connection
        return connection

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
            return self._get_connection().execute(sql, parameters)

    def on_exit(self):
        connection = getattr(self._local, 'connection', None)
        if connection is not None:
            connection.close()
            self._local.connection = None
