from src.utils.escape_code import ESCAPE_CODE as EC

class DashEmpty:
    def __repr__(self):
        return f'{EC.yellow}{EC.bold}{EC.dim}[EMPTY]{EC.rs}'
    
    def __eq__(self, value):
        if not isinstance(value, DashEmpty):
            return NotImplemented
        else:
            return self is value

    def __hash__(self):
        return id(self)

DASH_EMPTY = DashEmpty()