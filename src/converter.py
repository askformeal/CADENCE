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

CONVERTER = Converter()