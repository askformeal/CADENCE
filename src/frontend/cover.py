from src.utils.misc import base642bytes, hash_bytes

class Cover:
    def __init__(self, requester, placeholder, logger):
        self.request = requester
        self.placeholder = placeholder
        self.logger = logger
        self.cover = None
        self.old_cover_hash = None
        self.cover_cache = {}

    def get_cover(self, cover_hash):
        if cover_hash != self.old_cover_hash:
            self.old_cover_hash = cover_hash
            cover = self.request('get_cover')
            if cover is not None and cover.get('cover', None) is not None:
                self.cover = base642bytes(cover['cover'])
                self.old_cover_hash = hash_bytes(self.cover)
            else:
                self.cover = self.placeholder

        return self.cover