import readchar

DASH_POLL_INTERVAL = 0.1

DASH_MIN_WIDTH = 50
DASH_MAX_SHOW_SONG = 30
DASH_MAX_SHOW_LYRIC = 3
DASH_MAX_SHOW_BIND = 25
DASH_VOL_BAR_LEN = 20
DASH_TOAST_TIME = 5

CHAR_TO_NAME = {}

for key, value in vars(readchar.key).items():
    if isinstance(value, str):
        CHAR_TO_NAME[value] = key

class Bind:
    def __init__(self, *keys, name=None):
        self.chars = []
        self.key_names = []
        for key in keys:
            self.chars.append(key)
            self.key_names.append(CHAR_TO_NAME.get(key, key))

        if name is None:
            self.name = '[???]'
        else:
            self.name = name

    def __call__(self, key):
        return key in self.chars

    def __contains__(self, item):
        return item in self.chars

class DashKeyMap: # why not a dict? because this works better with my IDE's suggestions
    def __init__(self):
        self.open = Bind('o', name='Open')
        self.play_all = Bind(readchar.key.CTRL_A, name='Play All')
        self.toggle = Bind(readchar.key.SPACE, name='Play/Pause')
        self.stop = Bind('x', name='Stop Playback')
        self.dice = Bind('d', name='Dice')

        self.seek = Bind('g', name='Jump to Time')
        self.forward = Bind('.', 'l', readchar.key.RIGHT, name='Jump Forward')
        self.backward = Bind(',', 'h', readchar.key.LEFT, name='Jump Backward')

        self.shuffle = Bind('s', name='Toggle Shuffle')
        self.loop = Bind('r', name='Toggle Loop')

        self.vol_up = Bind('=', name='Volume Up')
        self.vol_down = Bind('-', name='Volume Down')
        self.mute = Bind('m', name='Toggle Mute')

        self.prev = Bind('p', name='Switch to Previous Song')
        self.next = Bind('n', name='Switch to Next Song')

        self.select_up = Bind('k', readchar.key.UP, name='Select Previous')
        self.select_down = Bind('j', readchar.key.DOWN, name='Select Next')
        self.select_current = Bind('c', name='Select Current Song')

        self.page_up = Bind(readchar.key.PAGE_UP, name='Page Up')
        self.page_down = Bind(readchar.key.PAGE_DOWN, name='Page Down')

        self.home = Bind(readchar.key.HOME, name='Go to top')
        self.end = Bind(readchar.key.END, name='Go to end')

        self.filter = Bind('/', name='Filter Playlist')

        self.switch_select = Bind(readchar.key.ENTER, name='Switch to Selected Song')

        self.help = Bind('?', readchar.key.F1, name='Show Help')

        self.next_box = Bind('t', name='Switch to Next Box Style')
        self.prev_box = Bind('T', name='Switch to Previous Box Style')
        self.redraw = Bind(readchar.key.CTRL_L, readchar.key.F5, name='Redraw Interface')

        self.quit = Bind('q', readchar.key.CTRL_C, readchar.key.CTRL_Z, name='Quit CADENCE Dashboard')

DASH_KEY_MAP = DashKeyMap()