import random

from src.utils.misc import base642bytes, hash_bytes
from src.constants.frontend import MAX_COVER_CACHE

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
            if cover_hash in self.cover_cache.keys():
                self.cover = self.cover_cache[cover_hash]
                self.logger.debug(f'Hit cached cover by hash {cover_hash}')
                self.logger.debug(f'Current cached size: {len(self.cover_cache)} entries')
            else:
                cover = self.request('get_cover')
                if cover is not None and cover.get('cover', None) is not None:
                    self.cover = base642bytes(cover['cover'])
                    self.old_cover_hash = hash_bytes(self.cover)
                    self.cover_cache[self.old_cover_hash] = self.cover
                else:
                    self.cover = self.placeholder

        if len(self.cover_cache) > MAX_COVER_CACHE:
            del_hash = random.choice(list(self.cover_cache.keys()))
            del self.cover_cache[del_hash]
            self.logger.debug(f'Max cover cache size reached, deleted entry with hash {del_hash}')

        return self.cover
