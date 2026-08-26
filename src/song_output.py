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

        self.duration = format_time(info.get('duration', -1))
        self.bitrate = info.get('bitrate', '?')
        if isinstance(self.bitrate, int):
            self.bitrate = f'{self.bitrate/1000:.10g}'
        self.sample_rate = info.get('sample_rate', '?')
        self.channels = info.get('channels', '?')

        self.path = info.get('path', '?')

        self.in_lib = {True: 'Yes', False: 'No', '?': '?'}[info.get('in_library', '?')]
        self.lib_id = info.get('id', '?')

        self.aliases = info.get('aliases', '?')
        self.aliases_num = '?'
        if self.aliases != '?':
            self.aliases_num = len(self.aliases)
            if len(self.aliases) > 0:
                self.aliases = ', '.join(self.aliases)
            else:
                self.aliases = 'No aliases are bond to this song'

        self.playlists = info.get('playlists', '?')
        self.playlists_num = '?'
        if self.playlists != '?':
            self.playlists_num = len(self.playlists)
            if len(self.playlists) > 0:
                self.playlists = ', '.join(self.playlists)
            else:
                self.playlists = '[This song is not in any playlists]'

        self.player_status = info.get('player_status', '?')

        raw_time = info.get('time', -1)
        raw_length = info.get('length', -1)

        self.time = format_time(raw_time)
        self.length = format_time(raw_length)
    
        if raw_length != -1:
            self.percentage = f'{raw_time / raw_length * 100:.0f}'
        else:
            self.percentage = '--'

        self.volume = info.get('volume', '?')
        self.mute = {True: 'Yes', False: 'No', '?': '?'}[info.get('mute', '?')]

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