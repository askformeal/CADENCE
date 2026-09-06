from .logger import logger
from src.sentinels import SENTINELS

class PlaylistMixin:
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

    def get_playlist_last_num(self, id):
        row = self.execute('SELECT last_num FROM playlists WHERE id = ?', id).fetchone()
        if row is None:
            logger.debug(f'Failed to get last played number of playlist with id {id} because it does not exists')
            return SENTINELS.PLAYLIST_NOT_FOUND
        else:
            logger.debug(f"Got last played number of playlist with id {id}: {row['last_num']}")
            return row['last_num']

    def set_playlist_last_num(self, id, num):
        if self.playlist_exists(id):
            self.execute('UPDATE playlists SET last_num = ? WHERE id = ?', num, id)
            logger.debug(f'Set the last played number of playlist with id {id} to {num}')
        else:
            logger.debug(f'Failed to the last played number of playlist with id {id} to {num} because the playlist does not exist')


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