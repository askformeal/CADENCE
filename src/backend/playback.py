import random
from threading import Thread

import syncedlyrics

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.config import CONFIG
from src.sentinels import SENTINELS
from src.utils.misc import get_song_display_name
from src.utils.lyric import parse_lyric

logger = setup_logger(__name__, BACKEND_LOG_PATH)

class Playback:
    def __init__(self, database):
        self.database = database

        self.loop = False
        self.shuffle = CONFIG.default_shuffle
        self.shuffle_order = []
        self.current_song_info = None
        self.current_song_num = None
        self.current_song_in_lib = False
        self.current_playlist = None
        self.online_lyric = CONFIG.default_online_lyric
        self.lyric = {}

    def get_playing_info(self):
        return self.current_song_info[self.current_song_num]

    def set_current_num(self, num, update_database=True):
        self.current_song_num = num

        if update_database and self.current_playlist is not None:
            if self.current_playlist is SENTINELS.PLAY_ALL:
                self.database.set_setting('last_play_all_num', num)
            else:
                self.database.set_playlist_last_num(self.current_playlist, num)

        logger.info(f'Updated current playlist number to {num}')

    def set_current_song(self, info, in_lib=True):
        if not isinstance(info, list):
            info = [info]
        self.current_song_info = info
        self.current_song_in_lib = in_lib
        self.set_current_num(0, update_database=False)
        self.shuffle_order = list(range(len(self.current_song_info)))
        if self.shuffle:
            random.shuffle(self.shuffle_order)
        logger.info(f'Set current info of current songs to {info}, in library {in_lib}')

    def get_current_display_name(self):
        if self.current_song_info is None or self.current_song_num >= len(self.current_song_info):
            return 'no song playing'
        else:
            return get_song_display_name(self.get_playing_info())

    def update_lyric(self):
        if self.current_song_info is not None:
            info = self.get_playing_info()
            song_path = info.get('path', None)
            if self.lyric.get('path', None) != song_path or self.lyric.get('online', None) != self.online_lyric:
                if self.online_lyric:
                    self.lyric = {'path': song_path, 'online': True, 'loading': True, 'lyric': None}
                    name = get_song_display_name(info)
                    artist = info.get('artist', None)
                    if artist is None:
                        artist = ''
                    Thread(target=self._fetch_lyric, args=(song_path, f'{name} {artist}'.strip())).start()
                else:
                    self.lyric = {'path': song_path, 'online': False, 'lyric': None}
                    lyric_path = info.get('lyric', None)
                    if lyric_path is not None:
                        lyric = parse_lyric(lyric_path)
                        if lyric is not SENTINELS.FILE_IO_FAILED:
                            self.lyric['lyric'] = lyric
                    

    def _fetch_lyric(self, song_path, search_term):
        try:
            result = syncedlyrics.search(
                search_term,
                synced_only=True,
            )
        except Exception:
            result = None

        if song_path == self.lyric.get('path') and self.lyric.get('online', False):
            self.lyric['loading'] = False
            if result is not None:
                lrc = parse_lyric(content=result)
                self.lyric['lyric'] = lrc