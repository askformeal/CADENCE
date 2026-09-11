from src.config import CONFIG

class EscapeCode:
    def __init__(self):
        self._set_vars()

    def _set_vars(self):
        self.reset = 0
        self.rs = 0
        self.bold = 1
        self.dim = 2
        self.italics = 3
        self.under = 4
        self.wave = '4:3'
        self.fast_flash = 5
        self.slow_flash = 6
        self.reverse = 7
        self.hide = 8
        self.del_ = 9
        self.double_under = 21
        self.boarder = 51
        self.round_boarder = 52
        self.upper = 53

        self.black = 30
        self.red = 31
        self.green = 32
        self.yellow = 33
        self.blue = 34
        self.magenta = 35
        self.cyan = 36
        self.white = 37

        self.br_black = 90
        self.br_red = 91
        self.br_green = 92
        self.br_yellow = 93
        self.br_blue = 94
        self.br_magenta = 95
        self.br_cyan = 96
        self.br_white = 97

        self.black_bg = 40
        self.red_bg = 41
        self.green_bg = 42
        self.yellow_bg = 43
        self.blue_bg = 44
        self.magenta_bg = 45
        self.cyan_bg = 46
        self.white_bg = 47

        self.br_black_bg = 100
        self.br_red_bg = 101
        self.br_green_bg = 102
        self.br_yellow_bg = 103
        self.br_blue_bg = 104
        self.br_magenta_bg = 105
        self.br_cyan_bg = 106
        self.br_white_bg = 107

        for name, value in vars(self).items():
            setattr(self, name, f'\033[{value}m')

    def __getattribute__(self, name):
        if CONFIG.escape_char or name.startswith('_'):
            return object.__getattribute__(self, name)
        else:
            return ''

ESCAPE_CODE = EscapeCode()