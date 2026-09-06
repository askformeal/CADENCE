from .logger import logger
from src.constants import METADATA
from src.sentinels import SENTINELS

class SongMixin:
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
    
    def get_multi_song_aliases(self, ids):
        rows = self.execute(f'SELECT name, song_id FROM aliases WHERE song_id IN ({', '.join('?'*len(ids))})', *ids).fetchall()
        return list(map(lambda row: (row['song_id'], row['name']), rows))
    
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
        