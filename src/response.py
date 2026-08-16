class Response:
    def __init__(self):
        self.SUCCESS = self.response('Action successfully completed', code=0)
        self.INVALID_ACTION = self.response('invalid action')

    def success(self, msg, attachment=None):
        return self.response(msg=msg, code=0, attachment=attachment)

    def invalid_path(self, song):
        return self.response(f'\"{song}\" can not be parsed as a valid and existing path')

    def song_not_exist(self, action):
        return self.response(f'can not {action} because it does not exist in library')
    
    def playlist_not_exist(self, action):
        return self.response(f'can not {action} because the playlist does not exist in library')

    def missing_key(self, action, key):
        return self.response(f'{action} action(s) requires key \"{key}\" but it is not received')

    def player_empty(self, action):
        return self.response(f'can not {action} because no songs are being played')

    def not_playing_paused(self, action):
        return self.response(f'can not {action} because the player is neither playing nor paused')

    def vlc_error(self, action):
        return self.response(f'can not {action} because an internal VLC error occurred')

    def player_timeout(self, action):
        return self.response(f'can not {action} because timeout waiting for the action to complete')

    def pos_too_late(self, action):
        return self.response(f'can not {action} because the position to jump to is later than the end of the song')
    
    def response(self, msg='', code=1, attachment=None):
        if attachment is None:
            attachment = {}
        return {'code': code, 'msg': msg, 'attachment': attachment}

    def merge(self, *responses, attachment=None):
        messages = []
        codes = []

        for response in responses:
            if response is not None:
                messages.append(response['msg'])
                codes.append(response['code'])

        if len(codes) > 0:
            msg = ' | '.join(messages)
            code = max(codes)
            return self.response(msg, code, attachment=attachment)
        else:
            return self.response('', attachment=attachment)

gen_response = Response()