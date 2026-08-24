from src.constants import MIN_TIMEOUT

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

    def pos_float(self, value):
        value = float(value)
        if value < MIN_TIMEOUT:
            raise ValueError
        else:
            return value

    def percentage(self, value):
        value = int(value)

        if value not in range(0, 101):
            raise ValueError
        else:
            return value

CONVERTER = Converter()