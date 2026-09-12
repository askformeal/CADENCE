from src.utils.tui import window_list

def gen_playlist_text(snapshot, height, selected):
    
    current = None
    if isinstance(snapshot.current_num, int):
        try:
            current = snapshot.songs_nums.index(snapshot.current_num)
        except ValueError:
            ...

    current_songs = snapshot.current_songs
    if len(current_songs) == 0:
        songs_lines = ['[Empty]']
    else:
        songs_lines = window_list(current_songs, height, selected, current=current, filter=snapshot.filter)

    if snapshot.filter != '':
        songs_lines = [f'Filter: \"{snapshot.filter}\"', *songs_lines]

    songs_lines = ['Playlist', *songs_lines]

    text = '\n'.join(songs_lines)

    return text