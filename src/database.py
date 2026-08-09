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
            self.connection.execute("PRAGMA journal_mode = WAL").fetchone()
            self.connection.row_factory = sqlite3.Row

            self.cursor = self.connection.cursor()
            self._init_database()

    def _init_database(self):
        self.execute("PRAGMA foreign_keys = ON")
        self.execute('''CREATE TABLE IF NOT EXISTS songs (
                            id INTEGER NOT NULL PRIMARY KEY,
                            path TEXT NOT NULL UNIQUE COLLATE NOCASE
                        )''')

        self.execute('''CREATE TABLE IF NOT EXISTS aliases (
                            id INTEGER NOT NULL PRIMARY KEY,
                            name TEXT NOT NULL UNIQUE,
                            song_id INTEGER,
                            FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
                        )''')

        self.execute('''CREATE TABLE IF NOT EXISTS playlists (
                            id INTEGER NOT NULL PRIMARY KEY,
                            name TEXT NOT NULL UNIQUE COLLATE NOCASE
                        )''')

        self.execute('''CREATE TABLE IF NOT EXISTS playlist_songs (
                            playlist_id INTEGER NOT NULL,
                            song_id INTEGER NOT NULL,
                            PRIMARY KEY (playlist_id, song_id),
                            FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE, 
                            FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
                        )''')


    # Song

    def song_exists(self, id):
        row = self.execute('SELECT 1 FROM songs WHERE id = ?', id).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Checked the existence of song with id {id}, result: {result}')
        return result

    def get_all_song_info(self):
        info = []
        rows = self.execute('SELECT * from songs').fetchall()
        for row in rows:
            info.append(dict(row))
        logger.debug(f'Got information of {len(info)} songs')
        return info

    def get_song_info(self, ids):
        if not isinstance(ids, list):
            ids = [ids]
        rows = self.execute(f'SELECT * from songs WHERE id IN ({', '.join('?'*len(ids))})', *ids).fetchall()
        info = list(map(lambda row: dict(row), rows))
        logger.debug(f'Got information of songs {ids}: {info}')
        return info

    def get_song_aliases(self, id):
        if self.song_exists(id):
            aliases = []
            rows = self.execute('SELECT name FROM aliases WHERE song_id = ?', id).fetchall()
            for row in rows:
                aliases.append(row['name'])
            logger.debug(f'Got aliases of song with id {id}: {aliases}')
            return aliases
        else:
            logger.warning(f'Tried to get aliases of song with id {id} but it does not exist')
            return SENTINELS.SONG_NOT_FOUND

    def get_song_via_alias(self, alias):
        row = self.execute('SELECT song_id FROM aliases JOIN songs ON aliases.song_id = songs.id WHERE name = ?', alias).fetchone()
        if row is not None:
            id = row['song_id']
            logger.debug(f'Got song with alias {alias}, id: {id}')
            return id
        else:
            logger.debug(f'Failed to get song with alias {alias} because the alias does not exist')
            return SENTINELS.ALIAS_NOT_FOUND

    def get_song_via_path(self, path):
        row = self.execute('SELECT id FROM songs WHERE path = ?', path).fetchone()
        if row is not None:
            id = row['id']
            logger.debug(f'Got song with path {path}, id: {id}')
            return id
        else:
            logger.debug(f'Failed to get song with path {path} because no song in library possesses the path')
            return SENTINELS.SONG_NOT_FOUND

    def add_song(self, path) -> tuple[int, bool]: # return id of the song + whether it already exists and is ignored.
        cursor = self.execute('INSERT OR IGNORE INTO songs(path) VALUES (?)', path)
        ignored = cursor.rowcount != 1
        if ignored:
            song_id = self.execute('SELECT id FROM songs WHERE path = ?', path).fetchone()['id']
        else:
            song_id = cursor.lastrowid
        logger.debug(f'Tried to add song to library, path: {path}, ignored: {ignored}')
        return song_id, ignored

    def delete_song(self, id):
        if self.song_exists(id):
            self.execute('DELETE FROM songs WHERE id = ?', id)
            logger.debug(f'Deleted song with id {id}')
            return SENTINELS.SUCCESS

        else:
            logger.debug(f'Failed to delete song with id {id} because it does not exist')
            return SENTINELS.SONG_NOT_FOUND

    # Alias

    def alias_exists(self, name):
        row = self.execute('SELECT 1 FROM aliases WHERE name = ?', name).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Check the existence of alias \"{name}\", result: {result}')
        return result

    def bind_alias(self, id, alias):
        if self.song_exists(id):
            if not self.alias_exists(alias):
                self.execute('INSERT INTO aliases(name, song_id) VALUES (?, ?)', alias, id)
                logger.debug(f'Bound alias \"{alias}\" to song with id {id}')
                return SENTINELS.SUCCESS
            else:
                logger.debug(f'Failed to bind alias \"{alias}\" to song with id {id} because it is already bound to another song')
                return SENTINELS.ALIAS_EXISTS
        else:
            logger.debug(f'Failed to bind alias \"{alias}\" to song with id {id} because the song does not exists')
            return SENTINELS.SONG_NOT_FOUND

    def unbind_alias(self, alias):
        if self.alias_exists(alias):
            self.execute('DELETE FROM aliases WHERE name = ?', alias)
            logger.debug(f'Deleted alias \"{alias}\"')
            return SENTINELS.SUCCESS
        else:
            logger.debug(f'Failed to deleted alias \"{alias}\" because it is not bound to any song')
            return SENTINELS.ALIAS_NOT_FOUND

    # Playlist

    def playlist_exists(self, id):
        row = self.execute('SELECT 1 FROM playlists WHERE id = ?', id).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Checked the existence of playlist with id {id}, result: {result}')
        return result

    def playlist_song_exists(self, playlist_id, song_id):
        row = self.execute('SELECT 1 FROM playlist_songs WHERE playlist_id = ? AND song_id = ?', playlist_id, song_id).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Check the existence of song with id {song_id} in playlist with id {playlist_id}, result: {result}')
        return result

    def get_all_playlists(self):
        rows = self.execute('SELECT * FROM playlists').fetchall()
        playlists = list(map(lambda row: dict(row), rows))
        logger.debug(f'Got information of {len(playlists)} playlist(s)')
        return playlists

    def get_song_playlists(self, id):
        rows = self.execute('SELECT playlist_id FROM playlist_songs WHERE song_id = ?', id).fetchall()
        playlists = list(map(lambda row: row['playlist_id'], rows))
        logger.debug(f'Got ids of playlist(s) contains song with id {id}: {playlists}')
        return playlists

    def get_playlist_via_name(self, name):
        row = self.execute('SELECT id FROM playlists WHERE name = ?', name).fetchone()
        if row is not None:
            id = row['id']
            logger.debug(f'Got playlist with name {name}, id: {id}')
            return id
        else:
            return SENTINELS.PLAYLIST_NOT_FOUND

    def get_playlist_songs(self, id):
        if self.playlist_exists(id):
            rows = self.execute('SELECT song_id FROM playlist_songs WHERE playlist_id = ?', id).fetchall()
            if len(rows) > 0:
                songs = list(map(lambda row: row['song_id'], rows))
                logger.debug(f'Got songs of playlist with id {id}: {songs}')
                return songs
            else:
                logger.debug(f'Failed to get songs of playlist with id {id} because the playlist is empty')
                return SENTINELS.PLAYLIST_EMPTY
        else:
            logger.debug(f'Failed to get songs of playlist with id {id} because the playlist does not exist')
            return SENTINELS.PLAYLIST_NOT_FOUND

    def create_playlist(self, name):
        cursor = self.execute('INSERT OR IGNORE INTO playlists (name) VALUES (?)', name)
        ignored = cursor.rowcount != 1
        if ignored:
            playlist_id = self.execute('SELECT id FROM playlists WHERE name = (?)', name).fetchone()['id']
        else:
            playlist_id = cursor.lastrowid
        logger.debug(f'Tried to add playlist to library, name: {name}, ignored: {ignored}')
        return playlist_id, ignored

    def del_playlist(self, playlist_id):
        if self.playlist_exists(playlist_id):
            self.execute('DELETE FROM playlists WHERE id=?', playlist_id)
            logger.debug(f'Deleted playlist with id {playlist_id}')
            return SENTINELS.SUCCESS
        else:
            logger.debug(f'Failed to delete playlist with id {playlist_id} because it does not exist')
            return SENTINELS.PLAYLIST_NOT_FOUND

    def add_song_to_playlist(self, playlist_id, song_id):
        if self.song_exists(song_id):
            if self.playlist_exists(playlist_id):
                cursor = self.execute('INSERT OR IGNORE INTO playlist_songs (playlist_id, song_id) VALUES (?, ?)', playlist_id, song_id)
                ignored = cursor.rowcount != 1
                logger.debug(f'Tried to add song with id {song_id} to playlist with id {playlist_id}, ignored: {ignored}')
                return ignored
            else:
                logger.debug(f'Failed to add song with id {song_id} to playlist with id {playlist_id} because the playlist does not exist')
                return SENTINELS.PLAYLIST_NOT_FOUND
        else:
            logger.debug(f'Failed to add song with id {song_id} to playlist with id {playlist_id} because the song does not exist')
            return SENTINELS.SONG_NOT_FOUND

    def del_song_from_playlist(self, playlist_id, song_id):
        if self.song_exists(song_id):
            if self.playlist_exists(playlist_id):
                if self.playlist_song_exists(playlist_id, song_id):
                    self.execute('DELETE FROM playlist_songs where playlist_id = ? AND song_id = ?', playlist_id, song_id)
                    logger.debug(f'Deleted song with id {song_id} from playlist with id {playlist_id}')
                    return SENTINELS.SUCCESS
                else:
                    logger.debug(f'Failed to delete song with id {song_id} from playlist with id {playlist_id} because the song is not in the playlist')
                    return SENTINELS.PLAYLIST_SONG_NOT_FOUND
            else:
                logger.debug(f'Failed to delete song with id {song_id} from playlist with id {playlist_id} because the playlist does not exist')
                return SENTINELS.PLAYLIST_NOT_FOUND
        else:
            logger.debug(f'Failed to delete song with id {song_id} from playlist with id {playlist_id} because the song does not exist')
            return SENTINELS.SONG_NOT_FOUND

    def reset(self):
        self.execute("PRAGMA foreign_keys = OFF")
        rows = self.execute('SELECT name FROM sqlite_master WHERE type = \'table\'').fetchall()
        tables = list(map(lambda row: row['name'], rows))
        for table in tables:
            self.execute(f'DROP TABLE IF EXISTS {table}')
        self._init_database()
        logger.debug('All tables dropped and recreated')
        
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