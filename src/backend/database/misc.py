import sqlite3

from .logger import logger

class MiscMixin:
    def _init_database(self):    
        INIT_DATABASE = [
            '''CREATE TABLE IF NOT EXISTS songs (
                id INTEGER NOT NULL PRIMARY KEY,
                name TEXT,
                artist TEXT,
                album TEXT,
                path TEXT NOT NULL UNIQUE COLLATE NOCASE
            )''',
    
            '''CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER NOT NULL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                song_id INTEGER,
                FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
            )''',
    
            '''CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER NOT NULL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE
                )''',
    
            '''CREATE TABLE IF NOT EXISTS playlist_songs (
                playlist_id INTEGER NOT NULL,
                song_id INTEGER NOT NULL,
                PRIMARY KEY (playlist_id, song_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE, 
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
            )''',
    
            '''CREATE TABLE IF NOT EXISTS positions (
                path TEXT NOT NULL PRIMARY KEY,
                position INTEGER NOT NULL
            )''',
    
            'ALTER TABLE songs ADD COLUMN duration INTEGER',
            'ALTER TABLE songs ADD COLUMN bitrate INTEGER',
            'ALTER TABLE songs ADD COLUMN sample_rate INTEGER',
            'ALTER TABLE songs ADD COLUMN channels INTEGER',
    
            '''CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )''',
    
            'ALTER TABLE playlists ADD COLUMN last_num INTEGER',
            'ALTER TABLE songs ADD COLUMN lyric TEXT',
            'ALTER TABLE songs ADD COLUMN offset INTEGER',
        ]
        version = self.execute('PRAGMA user_version').fetchone()[0]
        for i, sql in enumerate(INIT_DATABASE):
            if i + 1 > version:
                try:
                    self.execute(sql)
                except sqlite3.OperationalError as e:
                    logger.warning(f'Error while initializing database with {sql}: {e}')
                self.execute(f'PRAGMA user_version = {i+1}')

    def reset(self):
        # Let's break stuff
        # Delete the whole database and rebuild it
        self.execute("PRAGMA foreign_keys = OFF")
        rows = self.execute('SELECT name FROM sqlite_master WHERE type = \'table\'').fetchall()
        tables = list(map(lambda row: row['name'], rows))
        for table in tables:
            self.execute(f'DROP TABLE IF EXISTS {table}')

        self.execute(f'PRAGMA user_version = 0')

        self._init_database()
        logger.debug('All tables dropped and recreated')