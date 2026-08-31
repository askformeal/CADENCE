from pathlib import Path

from src.utils import format_time

class SongOutput:
    # generate outputs of from song info
    def __init__(self, info=None, prettify_none=True):
        if info is None:
            info = {}
        self.extract_from_dict(info, prettify_none=prettify_none)

    def extract_from_dict(self, info, prettify_none=True):

        self.name = info.get('name', '?')

        self.artist = info.get('artist', '?')
        self.album = info.get('album', '?')

        self.lyric = info.get('lyric', '?')
        self.lyric_raw = info.get('lyric', None)

        self.duration = format_time(info.get('duration', -1))
        self.bitrate = info.get('bitrate', '?')
        if isinstance(self.bitrate, int):
            self.bitrate = f'{self.bitrate/1000:.10g}'
        self.sample_rate = info.get('sample_rate', '?')
        self.channels = info.get('channels', '?')

        self.path = info.get('path', '?')

        self.in_lib = {True: 'Yes', False: 'No', '?': '?'}[info.get('in_library', '?')]
        self.in_lib_raw = info.get('in_library', None)
        self.lib_id = info.get('id', '?')
        self.lib_id_raw = info.get('id', None)

        self.aliases = info.get('aliases', '?')
        self.aliases_raw = info.get('aliases', [])

        self.aliases_num = '?'
        if self.aliases != '?':
            self.aliases_num = len(self.aliases)
            if len(self.aliases) > 0:
                self.aliases = ', '.join(self.aliases)
            else:
                self.aliases = 'No aliases are bond to this song'

        self.playlists = info.get('playlists', '?')
        self.playlists_raw = info.get('playlists', [])

        self.playlists_num = '?'
        if self.playlists != '?':
            self.playlists_num = len(self.playlists)
            if len(self.playlists) > 0:
                self.playlists = ', '.join(self.playlists)
            else:
                self.playlists = '[This song is not in any playlists]'

        self.player_status = info.get('player_status', '?')

        self.time_raw = info.get('time', None)
        self.length_raw = info.get('length', None)

        self.time = format_time(self.time_raw)
        self.length = format_time(self.length_raw)
    
        if self.length_raw is not None and self.time_raw is not None:
            self.percentage = f'{self.time_raw / self.length_raw * 100:.0f}'
        else:
            self.percentage = '--'

        self.volume = info.get('volume', '?')
        self.volume_raw = info.get('volume', None)

        self.mute = {True: 'On', False: 'Off', '?': '?'}[info.get('mute', '?')]
        self.mute_raw = info.get('mute', None)

        self.shuffle = {True: 'On', False: 'Off', '?': '?'}[info.get('shuffle', '?')]
        self.shuffle_raw = info.get('shuffle', None)

        self.loop = {True: 'On', False: 'Off', '?': '?'}[info.get('loop', '?')]
        self.loop_raw = info.get('loop', None)

        self.playlist_len = info.get('playlist_len', '?')

        self.current_num = info.get('current_num', '?')
        if isinstance(self.current_num, int):
            self.current_num += 1
    
        self.run_time = format_time(info.get('run_time', -1), 'sec')
    
        self.dev = info.get('dev', False)

        if self.name is None:
            if self.path != '?' and self.path is not None:
                self.display_name = Path(self.path).stem
            else:
                self.display_name = None
        else:
            self.display_name = self.name

        if prettify_none:
            for key, value in vars(self).items():
                if value is None:
                    setattr(self, key, 'N/A')