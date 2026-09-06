import random

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.config import CONFIG
from src.sentinels import SENTINELS
from src.utils import get_song_display_name

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