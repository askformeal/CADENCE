class Response:
    def __init__(self):
        self.SUCCESS = self.gen_response(code=0, msg='success')
        self.INVALID_ACTION = self.gen_response(msg='invalid action')
        self.VLC_ERROR = self.gen_response(msg='vlc error')
        self.EVENT_TIMEOUT = self.gen_response(msg='timeout waiting for completion')
        self.TOGGLE_FAILED = self.gen_response(msg='invalid player state, can not toggle')
        self.PAUSE_FAILED = self.gen_response(msg='can not pause because player is not playing')
        self.RESUME_FAILED = self.gen_response(msg='can not resume because player is not paused')
        self.EMPTY_PATHS = self.gen_response(msg='can not load empty path list')
        self.SWITCH_FAILED = self.gen_response(msg='can not switch music because the current playlist is empty')

    def gen_invalid_path(self, song):
        return self.gen_response(msg=f'\"{song}\" can not be parsed as a valid and existing path')

    def gen_song_exists(self, song):
        return self.gen_response(msg=f'can not add \"{song}\" because a song of the same path already exists in library')

    def gen_song_not_exist(self, action):
        return self.gen_response(msg=f'can not \"{action}\" because it does not exist in library')

    def gen_alias_exists(self, alias):
        return self.gen_response(msg=f'can not bind alias \"{alias}\" because it is already bound to another song in library')

    def gen_alias_not_exists(self, action):
        return self.gen_response(msg=f'can not \"{action}\" because it does not exist in library')

    def gen_playlist_empty(self, name):
        return self.gen_response(msg=f'can not open playlist \"{name}\" because it is empty')

    def gen_playlist_not_exist(self, name):
        return self.gen_response(msg=f'can not add song to playlist \"{name}\" because it does not exist in library')

    def gen_playlist_exists(self, name):
        return self.gen_response(msg=f'can not create \"{name}\" because a playlist of the same name already exists in library')

    def gen_playlist_song_exists(self, song, playlist):
        return self.gen_response(msg=f'can not add song \"{song}\" to playlist \"{playlist}\" because it is already in the playlist')

    def gen_missing_key(self, action, key):
        return self.gen_response(msg=f'\"{action}\" action(s) requires key \"{key}\" but it is not received')

    def gen_dispatch_failed(self, error):
        return self.gen_response(msg=f'failed to dispatch request: \"{error}\"')

    def gen_response(self, code=1, msg='', attachment=None):
        if attachment is None:
            attachment = {}
        return {'code': code, 'msg': msg, 'attachment': attachment}

response_template = Response()