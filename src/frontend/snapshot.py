from pathlib import Path

class Snapshot:
    def __init__(self, requester, empty=None):
        self.request = requester
        self.empty=empty
        self.snapshot = {}
        self._reset()

    def _reset(self):
        self.lib_id = self.empty
        self.display_name = self.empty
        self.meta_name = self.empty
        self.artist = self.empty
        self.album = self.empty
        
        self.time = self.empty
        self.length = self.empty
        
        self.volume = self.empty
        self.mute = self.empty
        
        self.shuffle = self.empty
        self.loop = self.empty
        
        self.current_num = self.empty # 0-based!
        self.playlist_len = self.empty
        self.current_songs = self.empty
        
        self.player_status = self.empty
        
        self.duration = self.empty
        self.bitrate = self.empty
        self.sample_rate = self.empty
        self.channels = self.empty
        
        self.aliases = self.empty
        self.added_playlists = self.empty
        self.lyric = self.empty
        self.online_lyric = self.empty
        self.lyric_loading = self.empty
        self.lyric_offset = self.empty
        self.offset_overlay = self.empty
        self.playlists = self.empty

    def poll(self):
        self._reset()
        self.snapshot = self.request('poll', silent=True)
        if self.snapshot is not None:            
            self.lib_id = self.get('id')
            if self.snapshot.get('name', None) is not None:
                self.display_name = self.snapshot['name']
            elif self.snapshot.get('path', None) is not None:
                self.display_name = Path(self.snapshot['path']).stem
            else:
                self.display_name = self.empty

            self.meta_name = self.get('name')
            self.artist = self.get('artist')
            self.album = self.get('album')
            self.time = self.get('time')
            self.length = self.get('length')
            self.volume = self.get('volume')
            self.mute = self.get('mute')
            self.shuffle = self.get('shuffle')
            self.loop = self.get('loop')
            self.online_lyric = self.get('online_lyric')
            self.current_num = self.get('current_num') # 0-based
            self.playlist_len = self.get('playlist_len')
            self.player_status = self.get('player_status')

            self.duration = self.get('duration')
            self.bitrate = self.get('bitrate')
            self.sample_rate = self.get('sample_rate')
            self.channels = self.get('channels')
            self.aliases = self.get('aliases')
            self.added_playlists = self.get('added_playlists')

            self.lyric = self.get('lyric')
            self.lyric_loading = self.get('lyric_loading')
            self.lyric_offset = self.get('lyric_offset')
            self.offset_overlay = self.get('offset_overlay')
            self.current_songs = self.get('current_songs')
            self.playlists = self.get('playlists')

    def get(self, name):
        value = self.snapshot.get(name, self.empty)
        if value is None:
            value = self.empty
        return value