import sqlite3
import threading

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.constants import METADATA
from src.sentinels import SENTINELS

logger = setup_logger(__name__, BACKEND_LOG_PATH)

class Database:
    def __init__(self, database_path):
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

    def _init_database(self):

        self.execute('PRAGMA foreign_keys = ON')
        
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
            )'''
        ]
        version = self.execute('PRAGMA user_version').fetchone()[0]
        for i, sql in enumerate(INIT_DATABASE):
            if i + 1 > version:
                try:
                    self.execute(sql)
                except sqlite3.OperationalError as e:
                    logger.warning(f'Error while initializing database with {sql}: {e}')
                self.execute(f'PRAGMA user_version = {i+1}')
    # Song

    def song_exists(self, id):
        # if a song exists
        row = self.execute('SELECT 1 FROM songs WHERE id = ?', id).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Checked the existence of song with id {id}, result: {result}')
        return result

    def get_all_song_info(self):
        # info of all songs (playlist and aliases not included)
        info = []
        rows = self.execute('SELECT * from songs').fetchall()
        for row in rows:
            info.append(dict(row))
        logger.debug(f'Got information of {len(info)} songs')
        return info

    def get_song_info(self, ids):
        # info of songs
        if not isinstance(ids, list):
            ids = [ids]
        rows = self.execute(f'SELECT * from songs WHERE id IN ({', '.join('?'*len(ids))})', *ids).fetchall()
        info = list(map(lambda row: dict(row), rows))
        logger.debug(f'Got information of songs {ids}: {info}')
        return info

    def get_song_aliases(self, id):
        # all aliases bound to a song
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
        # get the song an alias was bound to
        row = self.execute('SELECT song_id FROM aliases JOIN songs ON aliases.song_id = songs.id WHERE aliases.name = ?', alias).fetchone()
        if row is not None:
            id = row['song_id']
            logger.debug(f'Got song with alias {alias}, id: {id}')
            return id
        else:
            logger.debug(f'Failed to get song with alias {alias} because the alias does not exist')
            return SENTINELS.ALIAS_NOT_FOUND

    def get_song_via_path(self, path):
        # get a song by its path
        row = self.execute('SELECT id FROM songs WHERE path = ?', path).fetchone()
        if row is not None:
            id = row['id']
            logger.debug(f'Got song with path {path}, id: {id}')
            return id
        else:
            logger.debug(f'Failed to get song with path {path} because no song in library possesses the path')
            return SENTINELS.SONG_NOT_FOUND

    def add_song(self, path) -> tuple[int, bool]: # return id of the song + whether it already exists and is ignored.
        # add a new song
        cursor = self.execute('INSERT OR IGNORE INTO songs(path) VALUES (?)', path)
        ignored = cursor.rowcount != 1
        if ignored:
            song_id = self.execute('SELECT id FROM songs WHERE path = ?', path).fetchone()['id']
        else:
            song_id = cursor.lastrowid
        logger.debug(f'Tried to add song to library, path: {path}, ignored: {ignored}')
        return song_id, ignored

    def delete_song(self, id):
        # delete a song
        if self.song_exists(id):
            self.execute('DELETE FROM songs WHERE id = ?', id)
            logger.debug(f'Deleted song with id {id}')
            return SENTINELS.SUCCESS

        else:
            logger.debug(f'Failed to delete song with id {id} because it does not exist')
            return SENTINELS.SONG_NOT_FOUND

    def get_song_meta(self, song_id, meta):
        # get a metadata of a song
        if meta in METADATA: # Seems odd if I put this in set_song_meta but no here
            if self.song_exists(song_id):
                row = self.execute(f'SELECT {meta} FROM songs WHERE id = ?', song_id).fetchone()
                logger.debug(f'Got metadata \"{meta}\" of song with id {song_id}: {row[meta]}')
                return row[meta]
            else:
                logger.warning(f'Failed to get metadata \"{meta}\" of song with id {song_id} because the song does not exist')
                return SENTINELS.SONG_NOT_FOUND
        else:
            logger.warning(f'Failed to get metadata \"{meta}\" of song with id {song_id} because \"{meta}\" is not a valid metadata')
            return SENTINELS.INVALID_META


    def set_song_meta(self, song_id, meta, value): # pass SENTINEL.CLEAR_META to value to delete metadata
        # set a metadata of a song
        if meta in METADATA: # To prevent SQL injection. Probably useless
            if self.song_exists(song_id):
                if value is SENTINELS.CLEAR_META: # bullshit code. don't complain
                    value = None

                self.execute(f'UPDATE songs SET {meta} = ? WHERE id = ?', value, song_id)
                logger.debug(f'Set metadata \"{meta}\" of song with id {song_id} to {value}')
                return SENTINELS.SUCCESS
            else:
                logger.warning(f'Failed to set metadata \"{meta}\" of song with id {song_id} to {value} because the song does not exist')
                SENTINELS.SONG_NOT_FOUND
                return SENTINELS.SONG_NOT_FOUND
        else:
            logger.warning(f'Failed to set metadata \"{meta}\" of song with id {song_id} to {value} because \"{meta}\" is not a valid metadata')
            return SENTINELS.INVALID_META

    # Alias

    def alias_exists(self, name):
        # is an alias exists
        row = self.execute('SELECT 1 FROM aliases WHERE name = ?', name).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Check the existence of alias \"{name}\", result: {result}')
        return result

    def bind_alias(self, id, alias):
        # bind an alias to a song
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
        # delete an alias
        if self.alias_exists(alias):
            self.execute('DELETE FROM aliases WHERE name = ?', alias)
            logger.debug(f'Deleted alias \"{alias}\"')
            return SENTINELS.SUCCESS
        else:
            logger.debug(f'Failed to deleted alias \"{alias}\" because it is not bound to any song')
            return SENTINELS.ALIAS_NOT_FOUND

    # Playlist

    def playlist_exists(self, id):
        # if a playlist exists
        row = self.execute('SELECT 1 FROM playlists WHERE id = ?', id).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Checked the existence of playlist with id {id}, result: {result}')
        return result

    def playlist_song_exists(self, playlist_id, song_id):
        # if a song is in a playlist
        row = self.execute('SELECT 1 FROM playlist_songs WHERE playlist_id = ? AND song_id = ?', playlist_id, song_id).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Check the existence of song with id {song_id} in playlist with id {playlist_id}, result: {result}')
        return result

    def get_all_playlists(self):
        # get info of all playlists
        rows = self.execute('SELECT * FROM playlists').fetchall()
        playlists = list(map(lambda row: dict(row), rows))
        logger.debug(f'Got information of {len(playlists)} playlist(s)')
        return playlists

    def get_playlists_info(self, ids):
        # info of playlists
        if not isinstance(ids, list):
            ids = [ids]
        rows = self.execute(f'SELECT * FROM playlists WHERE id IN ({', '.join('?' * len(ids))})', *ids).fetchall()
        info = list(map(lambda row: dict(row), rows))
        logger.debug(f'Got information of playlist {ids}: {info}')
        return info

    def get_song_playlists(self, id):
        # get all playlists that a song is in
        rows = self.execute('SELECT playlist_id FROM playlist_songs WHERE song_id = ?', id).fetchall()
        playlists = list(map(lambda row: row['playlist_id'], rows))
        logger.debug(f'Got ids of playlist(s) contains song with id {id}: {playlists}')
        return playlists

    def get_playlist_via_name(self, name):
        # get a playlist by its name
        row = self.execute('SELECT id FROM playlists WHERE name = ?', name).fetchone()
        if row is not None:
            id = row['id']
            logger.debug(f'Got playlist with name {name}, id: {id}')
            return id
        else:
            return SENTINELS.PLAYLIST_NOT_FOUND

    def get_playlist_songs(self, id):
        # get all songs in a playlist
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
        # create a new playlist
        cursor = self.execute('INSERT OR IGNORE INTO playlists (name) VALUES (?)', name)
        ignored = cursor.rowcount != 1
        if ignored:
            playlist_id = self.execute('SELECT id FROM playlists WHERE name = (?)', name).fetchone()['id']
        else:
            playlist_id = cursor.lastrowid
        logger.debug(f'Tried to add playlist to library, name: {name}, ignored: {ignored}')
        return playlist_id, ignored

    def del_playlist(self, playlist_id):
        # delete a playlist
        if self.playlist_exists(playlist_id):
            self.execute('DELETE FROM playlists WHERE id=?', playlist_id)
            logger.debug(f'Deleted playlist with id {playlist_id}')
            return SENTINELS.SUCCESS
        else:
            logger.debug(f'Failed to delete playlist with id {playlist_id} because it does not exist')
            return SENTINELS.PLAYLIST_NOT_FOUND

    def add_song_to_playlist(self, playlist_id, song_id):
        # add a song to a playlist
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
        # remove a song from a playlist
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

    # Position

    def pos_memorized(self, path, log=True):
        # if the pos of a path is memorized
        row = self.execute('SELECT 1 FROM positions WHERE path = ?', path).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        if log:
            logger.debug(f'Check if position of {path} is memorized, result {result}')
        return result

    def get_pos(self, path):
        # get the memorized pos of a path
        row = self.execute('SELECT position FROM positions WHERE path = ?', path).fetchone()
        if row is not None:
            logger.debug(f'Got position of {path}: {row['position']}ms')
            return row['position']
        else:
            logger.debug(f'Failed to get position of {path} because it is not memorized')
            return SENTINELS.POS_NOT_FOUND

    def set_pos(self, path, pos, log=True):
        # memorize the pos of a path
        if self.pos_memorized(path, log=log):
            self.execute('UPDATE positions SET position = ? WHERE path = ?', pos, path)
            msg = f'Updated memorized position of {path} to {pos}ms'
        else:
            msg = f'Create memorized position of {path} as {pos}ms'
            self.execute('INSERT INTO positions(path, position) VALUES (?, ?)', path, pos)
        if log:
            logger.debug(msg)
        self.connection.commit()
        return SENTINELS.SUCCESS

    def del_pos(self, path):
        # delete the memorized pos of a path
        if self.pos_memorized(path):
            self.execute('DELETE FROM positions WHERE path = ?', path)
            logger.debug(f'Deleted the position of {path} from memory')
            return SENTINELS.SUCCESS
        else:
            return SENTINELS.POS_NOT_FOUND

    # Settings

    def setting_exists(self, key):
        row = self.execute('SELECT 1 FROM settings WHERE key = ?', key).fetchone()
        if row is None:
            result = False
        else:
            result = True
        logger.debug(f'Checked the existence of setting {key}, result: {result}')
        return result

    def get_setting(self, key):
        row = self.execute('SELECT value FROM settings WHERE key = ?', key).fetchone()
        if row is None:
            logger.debug(f'Failed to get the value of setting \"{key}\" because it does not exist')
            return SENTINELS.SETTING_NOT_FOUND
        else:
            logger.debug(f'Got the value of setting \"{key}\": {row['value']}')
            return row['value']

    def set_setting(self, key, value):
        if self.setting_exists(key):
            self.execute('UPDATE settings SET value = ? WHERE key = ?', value, key)
            logger.debug(f'Updated setting \"{key}\" to \"{value}\"')
        else:
            self.execute('INSERT INTO settings(key, value) VALUES (?, ?)', key, value)
            logger.debug(f'Created setting \"{key}\" with value \"{value}\"')

    # Let's break stuff

    def reset(self):
        # Delete the whole database and rebuild it
        self.execute("PRAGMA foreign_keys = OFF")
        rows = self.execute('SELECT name FROM sqlite_master WHERE type = \'table\'').fetchall()
        tables = list(map(lambda row: row['name'], rows))
        for table in tables:
            self.execute(f'DROP TABLE IF EXISTS {table}')

        self.execute(f'PRAGMA user_version = 0')

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