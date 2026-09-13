from .empty import DASH_EMPTY as EMPTY

class InfoMixin:
    def gen_info_text(self):
        if self.snapshot.aliases is EMPTY:
            aliases = EMPTY
        else:
            aliases = '\n  '.join(self.snapshot.aliases)

        if self.snapshot.added_playlists is EMPTY:
            playlists = EMPTY
        else:
            playlists = '\n  '.join(self.snapshot.added_playlists)

        lines = [
            'Information\n',
            f'Library ID: {self.snapshot.lib_id}',
            '',
            f'Duration: {self.snapshot.duration}',
            '',
            f'Name: {self.snapshot.meta_name}',
            f'Artist: {self.snapshot.artist}',
            f'Album: {self.snapshot.album}',
            '',
            f'Bitrate: {self.snapshot.bitrate} kbps',
            f'Sample Rate: {self.snapshot.sample_rate}',
            f'Channels: {self.snapshot.channels}',
            '',
            'Aliases:',
            f'  {aliases}',
            '',
            'Playlists:',
            f'  {playlists}'
        ]

        text = '\n'.join(lines)

        return text