class Response:
    def __init__(self):
        self.INVALID_ACTION = self.failed('invalid action')

    def _response(self, msg='', code=3, attachment=None, failed=None):
        if attachment is None:
            attachment = {}
        if failed is None:
            failed = []
        return {'code': code, 'msg': msg, 'attachment': attachment, 'failed': failed}

    def success(self, msg='', attachment=None, failed=None):
        return self._response(msg=msg, code=0, attachment=attachment, failed=failed)

    def failed(self, msg='', attachment=None, failed=None):
        return self._response(msg=msg, code=1, attachment=attachment, failed=failed)

    def invalid_path(self, song):
        return self.failed(f'\"{song}\" can not be parsed as a valid and existing path')

    def song_not_exist(self, action):
        return self.failed(f'can not {action} because it does not exist in library')
    
    def playlist_not_exist(self, action):
        return self.failed(f'can not {action} because the playlist does not exist in library')

    def missing_key(self, action, key):
        return self.failed(f'{action} action(s) requires key \"{key}\" but it is not received')

    def invalid_key_type(self, action, key, key_type):
        return self.failed(f'the value of key \"{key}\" of \"{action}\" action must be a {key_type} value but it is not')

    def player_empty(self, action):
        return self.failed(f'can not {action} because no songs are being played')

    def not_playing_paused(self, action):
        return self.failed(f'can not {action} because the player is neither playing nor paused')

    def vlc_error(self, action):
        return self.failed(f'can not {action} because an internal VLC error occurred')

    def player_timeout(self, action):
        return self.failed(f'can not {action} because timeout waiting for the action to complete')

    def pos_too_late(self, action):
        return self.failed(f'can not {action} because the position to jump to is later than the end of the song')

    def merge(self, *responses, attachment=None, failed=None):
        messages = []
        codes = []

        for response in responses:
            if response is not None:
                messages.append(response['msg'])
                codes.append(response['code'])

        if len(codes) > 0:
            msg = ' | '.join(messages)
            code = max(codes)
            return self._response(msg, code, attachment=attachment, failed=failed)
        else:
            return self._response('', attachment=attachment, failed=failed)

gen_response = Response()