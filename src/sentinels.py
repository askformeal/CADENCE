class Sentinel:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg
    
class Sentinels:
    def __init__(self):
        self.LOST = Sentinel('Connection Lost')
        self.EXIT_FLUSHING = Sentinel('Exit Flushing')
        self.SONG_NOT_FOUND = Sentinel('Song Not Found')
        self.PLAYLIST_NOT_FOUND = Sentinel('Playlist Not Found')
        self.PLAYLIST_SONG_NOT_FOUND = Sentinel('Playlist Song Not Found')
        self.PLAYLIST_EMPTY = Sentinel('Playlist Empty')
        self.ALIAS_EXISTS = Sentinel('Alias Already Exists')
        self.ALIAS_NOT_FOUND = Sentinel('Alias Not Found')
        self.DONE = Sentinel('Action Successfully Done') # when you don't have anything to return on success but something to return on failure
        self.NOT_IN_LIB = Sentinel('Song Not in Library')
        self.BACKEND_ALREADY_RUNNING = Sentinel('Backend is Already Running')
        self.BACKEND_STARTED = Sentinel('Backend Started')
        self.FAILED_START_BACKEND = Sentinel('Failed to Start Backend')

SENTINELS = Sentinels()