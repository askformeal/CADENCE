from src.sentinels import SENTINELS

from .logger import logger
from src.frontend.song_output import SongOutput

class Snapshot:
    def __init__(self, requester):
        self.request = requester
        self.filter = ''
        self._reset()

    def _reset(self):
        self.lib_id = None
        self.display_name = '[MISSING]'
        self.meta_name = '[MISSING]'
        self.artist = '[MISSING]'
        self.album = '[MISSING]'
        
        self.time = '[MISSING]'
        self.length = '[MISSING]'
        
        self.volume = '[MISSING]'
        self.mute = '[MISSING]'
        
        self.shuffle = '[MISSING]'
        self.loop = '[MISSING]'
        
        self.current_num = '[MISSING]' # 0-based!
        self.playlist_len = '[MISSING]'
        self.current_songs = ['[MISSING]']
        
        self.player_status = '[MISSING]'
        
        self.duration = '[MISSING]'
        self.bitrate = '[MISSING]'
        self.sample_rate = '[MISSING]'
        self.channels = '[MISSING]'
        
        self.aliases = ['[MISSING]']
        self.added_playlists = ['[MISSING]']
        self.lyric = {}
        self.songs_nums = [] # to prevent selected_song -> actual number in playlist mismatch when filter is applied

    def poll(self):
        self._reset()
        status = self.request('status', silent=True)
        if status is not None:
            status = SongOutput(status, prettify_none=False)
            self.lib_id = status.lib_id_raw
            self.display_name = status.display_name
            self.meta_name = status.name
            self.artist = status.artist
            self.album = status.album
            self.time = status.time_raw
            self.length = status.length_raw
            self.volume = status.volume
            self.mute = status.mute_raw
            self.shuffle = {True: '[Shuffle] ', False: '', None: '?'}[status.shuffle_raw]
            self.loop = {True: '[Loop] ', False: '', None: '?'}[status.loop_raw]
            self.online_lyric = {True: '[Ol Lyric] ', False: '', None: '?'}[status.online_lyric_raw] # why Ol and not Online? I need to make this as narrow as possible things won't get messy in small terminal windows
            self.current_num = status.current_num
            if isinstance(self.current_num, int):
                self.current_num -= 1
            self.playlist_len = status.playlist_len
            self.player_status = status.player_status
            if self.player_status is None:
                self.player_status = 'N/A'
            else:
                self.player_status = f'[{self.player_status.capitalize()}]'

        if self.lib_id is not None:
            info = self.request('lib.info', 
                                songs=[str(self.lib_id)], 
                                show_aliases=True, 
                                show_playlists=True, 
                                force_id=True, 
                                silent=True)
            if info is not None and len(info) > 0:
                info = SongOutput(info[0], prettify_none=False)
                self.duration = info.duration

                self.bitrate = info.bitrate
                self.sample_rate = info.sample_rate
                self.channels = info.channels

                self.aliases = info.aliases_raw
                self.added_playlists = info.playlists_raw

        if self.player_status != 'N/A':
            lyric = self.request('get_lyric', silent=True)
            if lyric is not None:
                if lyric.get('loading', False):
                    self.lyric = SENTINELS.LYRIC_LOADING
                else:
                    self.lyric = lyric.get('lyric', None)
                    if self.lyric is None:
                        self.lyric = []

        songs = self.request('list', silent=True)
        if songs is not None:
            if len(songs) == 0:
                self.current_songs = ['Player Empty']
            else:
                self.current_songs = []
                self.songs_nums = []
                for i, song in enumerate(songs):
                    song = SongOutput(song)
                    filter = self.filter.lower()
                    if filter in song.display_name.lower() or filter in song.artist.lower():
                        song_info = f'{song.display_name} - {song.artist}'
                        self.current_songs.append((song_info))
                        self.songs_nums.append(i)

                if len(self.current_songs) == 0:
                    self.current_songs = ['No matches of filter']