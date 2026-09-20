LOOP_INTERVAL = 0.05
PLAY_DEAD_TIME = 5

PLAYER_POLL_INTERVAL = 0.05
PLAYER_END_POLL_INTERVAL = 0.05
PLAYER_END_REDUNDANCY = 50 # ms

LYRIC_FETCH_MAX_WORKERS = 4

METADATA = ['name', 'artist', 'album', 'duration', 'bitrate', 'sample_rate', 'channels', 'lyric', 'offset']
SEARCH_META = ['name', 'artist', 'album'] # metadata that can be used for searching

FILE_META = {
    'title': 'name',
    'artist': 'artist',
    'album': 'album'
}

COVER_NAMES = ('cover', 'folder', 'album', 'albumart', 'front')
COVER_EXTENSIONS = ('.jpg', '.jpeg', '.png')

MAX_COVER_SIDE = 512
COVER_QUALITY = 85
