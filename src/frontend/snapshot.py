from src.sentinels import SENTINELS

from src.frontend.song_output import SongOutput

class Snapshot:
    def __init__(self, requester, missing=None, status=False, info=False, lyric=False, current_songs=False, playlists=False):
        self.request = requester
        self.missing=missing
        self.poll_status = status
        self.poll_info = info
        self.poll_lyric = lyric
        self.poll_current_songs = current_songs
        self.poll_playlists = playlists
        self.filter = ''
        self._reset()

    def _reset(self):
        self.lib_id = None
        self.display_name = self.missing
        self.meta_name = self.missing
        self.artist = self.missing
        self.album = self.missing
        
        self.time = self.missing
        self.length = self.missing
        
        self.volume = self.missing
        self.mute = self.missing
        
        self.shuffle = self.missing
        self.loop = self.missing
        
        self.current_num = self.missing # 0-based!
        self.playlist_len = self.missing
        self.current_songs = [self.missing]
        
        self.player_status = self.missing
        
        self.duration = self.missing
        self.bitrate = self.missing
        self.sample_rate = self.missing
        self.channels = self.missing
        
        self.aliases = [self.missing]
        self.added_playlists = [self.missing]
        self.lyric = {}
        self.online_lyric = self.missing
        self.lyric_offset = 0
        self.offset_overlay = 0
        self.songs_nums = [] # to prevent selected_song -> actual number in playlist mismatch when filter is applied
        self.playlists = [self.missing]

    def poll(self):
        self._reset()

        if self.poll_status:
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
                self.shuffle = status.shuffle_raw
                self.loop = status.loop_raw
                self.online_lyric = status.online_lyric_raw # why Ol and not Online? I need to make this as narrow as possible things won't get messy in small terminal windows
                self.current_num = status.current_num
                if isinstance(self.current_num, int):
                    self.current_num -= 1
                self.playlist_len = status.playlist_len
                self.player_status = status.player_status

        if self.poll_info and self.lib_id is not None:
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

        if self.poll_lyric:
            lyric = self.request('get_lyric', silent=True)
            if lyric is not None:
                if lyric.get('loading', False):
                    self.lyric = SENTINELS.LYRIC_LOADING
                else:
                    self.lyric = lyric.get('lyric', None)
                    if self.lyric is None:
                        self.lyric = []
                    self.lyric_offset = lyric.get('offset', 0)
                    self.offset_overlay = lyric.get('offset_overlay', 0)

        if self.poll_current_songs:
            songs = self.request('list', silent=True)
            if songs is not None:
                self.current_songs = []
                self.songs_nums = []
                if len(songs) > 0:
                    for i, song in enumerate(songs):
                        song = SongOutput(song)
                        filter = self.filter.lower()
                        if filter in song.display_name.lower() or filter in song.artist.lower():
                            song_info = f'{song.display_name} - {song.artist}'
                            self.current_songs.append((song_info))
                            self.songs_nums.append(i)

                    if len(self.current_songs) == 0:
                        self.current_songs = ['No matches of filter']

        if self.poll_playlists:
            playlists = self.request('lib.playlist.list', silent=True)
            if playlists is not None:
                self.playlists = list(map(lambda x: x['name'], playlists))
                