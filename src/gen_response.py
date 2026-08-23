class Response:
    def __init__(self, msg=None, code=None, attachment=None, failed=None):
        if code is None:
            self.code = 3
        else:
            self.code = code

        if msg is None:
            self.msg = 'undefined message'
        else:
            self.msg = msg

        if attachment is None:
            self.attachment = {}
        else:
            self.attachment = attachment

        if failed is None:
            self.failed = []
        else:
            self.failed = failed

    def __repr__(self):
        return str(dict(self))

    def keys(self):
        return vars(self).keys()

    def __getitem__(self, key):
        # this is for dict(). do not access attr with [], use the dot.
        return getattr(self, key)

    def __add__(self, other):
        return merge(self, other)

    def __iadd__(self, other):
        self.append(other)
        return self
    
    def ok(self):
        return self.code == 0
    
    def append(self, *responses, **kwargs):
        result = merge(self, *responses, **kwargs)
        
        self.code = result.code
        self.msg = result.msg
        if result.attachment != {}:
            self.attachment = result.attachment

        if result.failed != []:
            self.failed = result.failed

class Success(Response):
    def __init__(self, msg=None, attachment=None, failed=None):
        super().__init__(msg, 0, attachment, failed)

class Failed(Response):
    def __init__(self, msg=None, attachment=None, failed=None):
        super().__init__(msg, 1, attachment, failed)

class BatchAuto(Response):
    def __init__(self, action, failed_num, total_num, attachment=None, failed=None):
        if failed_num < total_num:
            code = 0
        else:
            code = 1

        super().__init__(f'{action} [{total_num-failed_num}/{total_num}]', code, attachment, failed)

class Dying(Response):
    def __init__(self):
        super().__init__('backend is dying', code=4)

class Undefined(Response):
    def __init__(self):
        super().__init__('undefined response', code=3)

class UnknownAction(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'unknown action received: \"{action}\"', attachment, failed)

class InvalidPath(Failed):
    def __init__(self, song, attachment=None, failed=None):
        super().__init__(f'\"{song}\" can not be parsed as a valid and existing path', attachment, failed)

class SongNotExist(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because it does not exist in library', attachment, failed)
    
class PlaylistNotExist(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because the playlist does not exist in library', attachment, failed)

class MissingKey(Failed):
    def __init__(self, action, key, attachment=None, failed=None):
        super().__init__(f'{action} action(s) requires key \"{key}\" but it is not received', attachment, failed)

class InvalidKeyType(Failed):
    def __init__(self, action, key, key_type, received_type, attachment=None, failed=None):
        super().__init__(f'the value of key \"{key}\" of \"{action}\" action must be a {key_type} value but a value of type \"{received_type}\" was received instead', attachment, failed)

class InvalidElementType(Failed):
    def __init__(self, action, key, element_type, received_type, attachment=None, failed=None):
        super().__init__(f'every element of the value of the key \"{key}\" of \"{action}\" action must be a {element_type} value but one with value of type \"{received_type}\" was received instead', attachment, failed)

class EmptyList(Failed):
    def __init__(self, item, attachment=None, failed=None):
        super().__init__(f'received empty list of {item}', attachment, failed)

class PercentageTooLow(Failed):
    def __init__(self, value, attachment=None, failed=None):
        super().__init__(f'{value} is lower than 0 and hence not a valid percentage number', attachment, failed)

class PercentageTooHigh(Failed):
    def __init__(self, value, attachment=None, failed=None):
        super().__init__(f'{value} is higher than 100 and hence not a valid percentage number', attachment, failed)

class PlayerEmpty(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because no songs are being played', attachment, failed)

class NotPlayingPaused(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because the player is neither playing nor paused', attachment, failed)

class VLCError(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because an internal VLC error occurred', attachment, failed)

class PlayerTimeout(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because timeout waiting for the action to complete', attachment, failed)

class PosTooLate(Failed):
    def __init__(self, action, attachment=None, failed=None):
        super().__init__(f'can not {action} because the position to jump to is later than the end of the song', attachment, failed)

def merge(*responses: Response, joiner='|', attachment=None, failed=None):
    messages = []
    codes = []

    for response in responses:
        if response is not None:
            messages.append(response.msg)
            codes.append(response.code)

    if len(codes) > 0:
        msg = f' {joiner} '.join(messages)
        code = max(codes)
        return Response(msg, code, attachment=attachment, failed=failed)
    else:
        return Response('', attachment=attachment, failed=failed)