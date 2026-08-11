class Response:
    def __init__(self):
        self.SUCCESS = self.gen_response('Action successfully completed', code=0)
        self.INVALID_ACTION = self.gen_response('invalid action')

    def gen_invalid_path(self, song):
        return self.gen_response(f'\"{song}\" can not be parsed as a valid and existing path')

    def gen_song_not_exist(self, action):
        return self.gen_response(f'can not {action} because it does not exist in library')
    
    def gen_playlist_not_exist(self, action):
        return self.gen_response(f'can not {action} because the playlist does not exist in library')

    def gen_missing_key(self, action, key):
        return self.gen_response(f'{action} action(s) requires key \"{key}\" but it is not received')

    def gen_player_empty(self, action):
        return self.gen_response(f'can not {action} because no songs are being played')

    def gen_vlc_error(self, action):
        return self.gen_response(f'can not {action} because an internal VLC error occurred')

    def gen_player_timeout(self, action):
        return self.gen_response(f'can not {action} because timeout waiting for the action to complete')

    def gen_pos_too_late(self, action):
        return self.gen_response(f'can not {action} because the position to jump to is later than the end of the song')
    
    def gen_response(self, msg='', code=1, attachment=None):
        if attachment is None:
            attachment = {}
        return {'code': code, 'msg': msg, 'attachment': attachment}

response_template = Response()