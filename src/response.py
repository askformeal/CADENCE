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

    def gen_song_exists(self, path):
        return self.gen_response(msg=f'can not add {path} because a song of the same path already exists in the library')

    def gen_missing_key(self, action, key):
        return self.gen_response(msg=f'\"{action}\" action(s) requires key \"{key}\" but it is not received')

    def gen_dispatch_failed(self, error):
        return self.gen_response(msg=f'failed to dispatch request: {error}')

    def gen_response(self, code=1, msg='', attachment=None):
        if attachment is None:
            attachment = {}
        return {'code': code, 'msg': msg, 'attachment': attachment}

response_template = Response()