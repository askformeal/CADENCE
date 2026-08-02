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
        self.ALIAS_EXISTS = Sentinel('Alias Already Exists')
        self.ALIAS_NOT_FOUND = Sentinel('Alias Not Found')
        self.DONE = Sentinel('Action Successfully Done') # when you don't have anything to return on success but something to return on failure

SENTINELS = Sentinels()