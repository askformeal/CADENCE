class Sentinel:
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg

    def __eq__(self, value):
        if not isinstance(value, Sentinel):
            return NotImplemented
        else:
            return self is value

    def __hash__(self):
        return id(self)
    
class Sentinels:
    def __init__(self):
        self.SUCCESS = Sentinel('Action Successfully Done') # when you don't have anything to return on success but something to return on failure

        # Config

        self.CONFIG_WRITE_FAILED = Sentinel('Failed to Write Into Configure File')
        self.UNKNOWN_OPTION = Sentinel('Tried to Get/Set an Unknown Option')
        self.OPTION_NOT_FOUND = Sentinel('Option Not Found')
        self.INVALID_OPTION_VALUE = Sentinel('Value of Option is Invalid')
        self.INVALID_CONFIG_FILE = Sentinel('Configure File is Not a Valid TOML File')

        # Connection
        self.LOST = Sentinel('Connection Lost')

        # Backend
        self.KEY_NOT_PROVIDED = Sentinel('Key not Provided in Request')
        self.SOURCE_NOT_PROVIDED = Sentinel('No source provided in request')
        self.MISSING_CWD = Sentinel('CWD is Needed but Missing')

        self.EXIT_FLUSHING = Sentinel('Exit Flushing')
        self.NOT_IN_LIB = Sentinel('Song Not in Library')

        self.PLAY_ALL = Sentinel('Play All Song in Library')

        # Database

        self.SONG_NOT_FOUND = Sentinel('Song Not Found')

        self.CLEAR_META = Sentinel('Clear This Metadata')
        self.INVALID_META = Sentinel('Metadata not supported')

        self.ALIAS_NOT_FOUND = Sentinel('Alias Not Found')
        self.ALIAS_EXISTS = Sentinel('Alias Already Exists')

        self.PLAYLIST_NOT_FOUND = Sentinel('Playlist Not Found')
        self.PLAYLIST_SONG_NOT_FOUND = Sentinel('Playlist Song Not Found')
        self.PLAYLIST_EMPTY = Sentinel('Playlist Empty')

        self.POS_NOT_FOUND = Sentinel('Position not in memory')

        self.SETTING_NOT_FOUND = Sentinel('Setting not found')

        # Player

        self.PLAYER_EMPTY = Sentinel('Current playlist is empty')
        self.PLAYER_LOAD_EMPTY = Sentinel('Tried to load empty list of paths')
        self.VLC_ERROR = Sentinel('A VLC error occurred')
        self.PLAYER_TIMEOUT = Sentinel('Timeout waiting for player action to complete')
        self.INVALID_PLAYER_STATE = Sentinel('This action can not be done under current player state')
        self.POS_TOO_LATE = Sentinel('Position is Later than Total Length')

        # Starter
        self.BACKEND_ALREADY_RUNNING = Sentinel('Backend is Already Running')
        self.BACKEND_STARTED = Sentinel('Backend Started')
        self.FAILED_START_BACKEND = Sentinel('Failed to Start Backend')

        # Process

        self.PERMISSION_INSUFFICIENT = Sentinel('Permission Insufficient')
        self.INVALID_PID = Sentinel('Invalid PID')
        self.PROCESS_NOT_FOUND = Sentinel('Process Not Found')
        self.GRACE_KILL = Sentinel('Process is Gracefully Terminated')
        self.FORCE_KILL = Sentinel('Process is Forcefully Killed')
        
        # Misc
        self.INVALID_TIME = Sentinel('Invalid Time, Can Not be Parsed')
        self.ROOT_SECTION = Sentinel('This Config Option is in the Root Section')
        self.FILE_IO_FAILED = Sentinel('Failed to Write/Read File')

SENTINELS = Sentinels()
