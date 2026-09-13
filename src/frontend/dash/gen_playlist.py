from src.utils.tui import window_list
from .empty import DASH_EMPTY as EMPTY

class PlaylistMixin:
    def gen_playlist_text(self):
        current = None
        if self.snapshot.current_num is not EMPTY:
            try:
                current = self.song_nums.index(self.snapshot.current_num)
            except ValueError:
                ...

        if len(self.filtered_songs) == 0:
            songs_lines = ['[Empty]']
        else:
            songs_lines = window_list(self.filtered_songs, 
                                      self.playlist_height, 
                                      self.song_selected, 
                                      current=current, 
                                      filter=self.filter)

        if self.filter != '':
            songs_lines = [f'Filter: \"{self.filter}\"', *songs_lines]

        songs_lines = ['Playlist', *songs_lines]

        text = '\n'.join(songs_lines)

        return text
    