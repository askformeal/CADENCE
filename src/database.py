import logging
import sqlite3
import threading

from src.constants import DATABASE_PATH
from src.sentinels import SENTINELS

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self._lock = threading.Lock()

        try:
            self.connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False, isolation_level=None)
        except sqlite3.Error as e:
            raise RuntimeError(f'Failed to connect to database: {e}') from e
        else:
            self.connection.execute("PRAGMA foreign_keys = ON")
            self.connection.execute("PRAGMA journal_mode = WAL").fetchone()
            self.connection.row_factory = sqlite3.Row

            self.cursor = self.connection.cursor()
            self._init_database()

    def _init_database(self):
        self.execute('''CREATE TABLE IF NOT EXISTS songs (
                        id INTEGER NOT NULL PRIMARY KEY,
                        path TEXT NOT NULL UNIQUE COLLATE NOCASE)''')

        self.execute('''CREATE TABLE IF NOT EXISTS aliases (
                        id INTEGER NOT NULL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        song_id INTEGER,
                        FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE)''')

    def song_exists(self, id):
        row = self.execute('SELECT 1 FROM songs WHERE id = ?', id).fetchone()
        if row is None:
            return False
        else:
            return True

    def get_all_song_info(self):
        info = []
        rows = self.execute('SELECT * from songs').fetchall()
        for row in rows:
            info.append(dict(row))

        return info

    def get_song_info(self, id):
        row = self.execute('SELECT * from songs where id = ?', id).fetchone()
        if row is not None:
            return dict(row)
        else:
            return SENTINELS.SONG_NOT_FOUND

    def get_song_aliases(self, id):
        if self.song_exists(id):
            aliases = []
            rows = self.execute('SELECT name FROM aliases WHERE song_id = ?', id).fetchall()
            for row in rows:
                aliases.append(row['name'])
            return aliases
        else:
            return SENTINELS.SONG_NOT_FOUND

    def get_song_via_alias(self, alias):
        row = self.execute('SELECT song_id FROM aliases JOIN songs ON aliases.song_id = songs.id WHERE name = ?', alias).fetchone()
        if row is not None:
            return row['song_id']
        else:
            return SENTINELS.ALIAS_NOT_FOUND

    def get_song_via_path(self, path):
        row = self.execute('SELECT id FROM songs WHERE path = ?', path).fetchone()
        if row is not None:
            return row['id']
        else:
            return SENTINELS.SONG_NOT_FOUND

    def add_song(self, path) -> tuple[int, bool]: # return id of the song + whether it already exists and is ignored.
        cursor = self.execute('INSERT OR IGNORE INTO songs(path) VALUES (?)', path)
        ignored = cursor.rowcount != 1
        if ignored:
            song_id = self.execute('SELECT id FROM songs WHERE path = ?', path).fetchone()['id']
        else:
            song_id = cursor.lastrowid
        logger.info(f'Tried to add song to library, path: {path}, ignored: {ignored}')
        return (song_id, ignored)

    def delete_song(self, id):
        if self.song_exists(id):
            self.execute('DELETE FROM songs WHERE id = ?', id)
            return SENTINELS.DONE

        else:
            return SENTINELS.SONG_NOT_FOUND

    def alias_exists(self, name):
        row = self.execute('SELECT 1 FROM aliases WHERE name = ?', name).fetchone()
        if row is None:
            return False
        else:
            return True

    def add_alias(self, name, id):
        if self.song_exists(id):
            if not self.alias_exists(name):
                self.execute('INSERT INTO aliases(name, song_id) VALUES (?, ?)', name, id)
                return SENTINELS.DONE
            else:
                return SENTINELS.ALIAS_EXISTS
        else:
            return SENTINELS.SONG_NOT_FOUND

    def delete_alias(self, name):
        if self.alias_exists(name):
            self.execute('DELETE FROM aliases WHERE name = ?', name)
            return SENTINELS.DONE
        else:
            return SENTINELS.ALIAS_NOT_FOUND
        
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