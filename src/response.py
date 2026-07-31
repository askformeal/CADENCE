class Response:
    def __init__(self):
        self.SUCCESS = {'code': 0, 'msg': 'success', 'attachment': {}}
        self.INVALID_ACTION = {'code': 1, 'msg': 'invalid action', 'attachment': {}}
        self.MISSING_ACTION = {'code': 1, 'msg': '\"action\" key not found', 'attachment': {}}
        self.VLC_ERROR = {'code': 1, 'msg': 'vlc error', 'attachment': {}}
        self.EVENT_TIMEOUT = {'code': 1, 'msg': 'timeout waiting for completion', 'attachment': {}}
        self.TOGGLE_FAILED = {'code': 1, 'msg': 'invalid player state, can not toggle', 'attachment': {}}
        self.EMPTY_PATHS = {'code': 1, 'msg': 'can not load empty path list', 'attachment': {}}

    def gen_missing_key(self, action, key):
        return {'code': 1, 'msg': f'\"{action}\" action requires key \"{key}\" but it is not received', 'attachment': {}}

    def gen_dispatch_failed(self, error):
        return {'code': 1, 'msg': f'failed to dispatch request: {error}', 'attachment': {}}

    def gen_response(self, code=1, msg='', attachment={}):
        return {'code': code, 'msg': msg, 'attachment': attachment}

response_template = Response()