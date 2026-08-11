class Sentinel:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg
    
class Sentinels:
    def __init__(self):
        self.SUCCESS = Sentinel('Action Successfully Done') # when you don't have anything to return on success but something to return on failure
        self.LOST = Sentinel('Connection Lost')
        self.EXIT_FLUSHING = Sentinel('Exit Flushing')
        self.SONG_NOT_FOUND = Sentinel('Song Not Found')
        self.PLAYLIST_NOT_FOUND = Sentinel('Playlist Not Found')
        self.PLAYLIST_SONG_NOT_FOUND = Sentinel('Playlist Song Not Found')
        self.PLAYLIST_EMPTY = Sentinel('Playlist Empty')
        self.ALIAS_EXISTS = Sentinel('Alias Already Exists')
        self.ALIAS_NOT_FOUND = Sentinel('Alias Not Found')
        self.POS_NOT_FOUND = Sentinel('Position not in memory')
        self.NOT_IN_LIB = Sentinel('Song Not in Library')
        self.MISSING_CWD = Sentinel('CWD is Needed but Missing')
        self.BACKEND_ALREADY_RUNNING = Sentinel('Backend is Already Running')
        self.BACKEND_STARTED = Sentinel('Backend Started')
        self.FAILED_START_BACKEND = Sentinel('Failed to Start Backend')

        self.PLAYER_EMPTY = Sentinel('Current playlist is empty')
        self.PLAYER_LOAD_EMPTY = Sentinel('Tried to load empty list of paths')
        self.VLC_ERROR = Sentinel('A VLC error occurred')
        self.PLAYER_TIMEOUT = Sentinel('Timeout waiting for player action to complete')
        self.INVALID_PLAYER_STATE = Sentinel('This action can not be done under current player state')
        self.POS_TOO_LATE = Sentinel('Position is Later than Total Length')

SENTINELS = Sentinels()
