LOOP_INTERVAL = 0.05
PLAY_DEAD_TIME = 5

PLAYER_POLL_INTERVAL = 0.05

METADATA = ['name', 'artist', 'album', 'duration', 'bitrate', 'sample_rate', 'channels', 'lyric']
SEARCH_META = ['name', 'artist', 'album'] # metadata that can be used for searching

FILE_META = {
    'title': 'name',
    'artist': 'artist',
    'album': 'album'
}

# file type descriptions, kept short like those used in file selectors
AUDIO_FILE_TYPES = (
    ('MP3 Audio', '.mp3'),
    ('FLAC Audio', '.flac'),
    ('WAV Audio', '.wav'),
    ('OGG Audio', '.ogg'),
    ('Opus Audio', '.opus'),
    ('OGG Audio', '.oga'),
    ('M4A Audio', '.m4a'),
    ('M4B Audio', '.m4b'),
    ('AAC Audio', '.aac'),
    ('MP4 Audio', '.mp4'),
    ('M4P Audio', '.m4p'),
    ('APE Audio', '.ape'),
    ('WMA Audio', '.wma'),
    ('AIFF Audio', '.aiff'),
    ('AIF Audio', '.aif'),
    ('AU Audio', '.au'),
    ('AC3 Audio', '.ac3'),
    ('DTS Audio', '.dts'),
    ('DSF Audio', '.dsf'),
    ('DSD Audio', '.dsd'),
    ('DFF Audio', '.dff'),
    ('MKA Audio', '.mka'),
    ('WV Audio', '.wv'),
    ('MPC Audio', '.mpc'),
    ('TTA Audio', '.tta'),
    ('TAK Audio', '.tak'),
    ('RA Audio', '.ra'),
    ('RM Audio', '.rm'),
    ('AMR Audio', '.amr'),
    ('3GP Audio', '.3gp'),
    ('CAF Audio', '.caf'),
    ('MIDI Audio', '.mid'),
    ('MIDI Audio', '.midi'),
    ('Speex Audio', '.spx'),
)

AUDIO_EXTENSIONS = set(map(lambda x: x[1], AUDIO_FILE_TYPES))