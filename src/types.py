
class IterType:
    # can be list or tuple
    def __init__(self, element_type):
        self.element_type = element_type

class Converter:
    def boolean(self, value):
        value = str(value)
        value = {
            'true': True,
            'false': False,
            '1': True,
            '0': False
        }.get(str(value).lower(), None)
        if value is None:
            raise ValueError
        else:
            return value

    def port(self, value):
        value = int(value) # if it's not a number, will raise ValueError as it should
        if value <= 0:
            raise ValueError
        else:
            return value

    def pos_int(self, value):
        value = int(value)
        if value <= 0:
            raise ValueError
        else:
            return value

    def non_neg_int(self, value):
        value = int(value)
        if value < 0:
            raise ValueError
        else:
            return value
        
    def timeout(self, value):
        value = float(value)
        from src.constants import MIN_TIMEOUT
        if value < MIN_TIMEOUT:
            raise ValueError
        else:
            return value

    def box_style(self, value):
        value = str(value)
        from src.constants import BOX_STYLES
        if value not in BOX_STYLES.keys():
            raise ValueError
        else:
            return value

    def percentage(self, value):
        value = int(value)

        if value not in range(0, 101):
            raise ValueError
        else:
            return value

    def hex_color(self, value):
        value = str(value).upper()
        if value.startswith('#') and len(value) == 7:
            for digit in value[1:]:
                if digit not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'):
                    break
            else:
                return value
            raise ValueError
        else:
            raise ValueError
CONVERTER = Converter()