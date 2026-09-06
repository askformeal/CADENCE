from .logger import logger
from src.sentinels import SENTINELS

class AliasMixin:
    def alias_exists(self, name):
        # is an alias exists
        row = self.execute('SELECT 1 FROM aliases WHERE name = ?', name).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        logger.debug(f'Check the existence of alias \"{name}\", result: {result}')
        return result
    
    def bind_alias(self, id, alias):
        # bind an alias to a song
        if self.song_exists(id):
            if not self.alias_exists(alias):
                self.execute('INSERT INTO aliases(name, song_id) VALUES (?, ?)', alias, id)
                logger.debug(f'Bound alias \"{alias}\" to song with id {id}')
                return SENTINELS.SUCCESS
            else:
                logger.debug(f'Failed to bind alias \"{alias}\" to song with id {id} because it is already bound to another song')
                return SENTINELS.ALIAS_EXISTS
        else:
            logger.debug(f'Failed to bind alias \"{alias}\" to song with id {id} because the song does not exists')
            return SENTINELS.SONG_NOT_FOUND
    
    def unbind_alias(self, alias):
        # delete an alias
        if self.alias_exists(alias):
            self.execute('DELETE FROM aliases WHERE name = ?', alias)
            logger.debug(f'Deleted alias \"{alias}\"')
            return SENTINELS.SUCCESS
        else:
            logger.debug(f'Failed to deleted alias \"{alias}\" because it is not bound to any song')
            return SENTINELS.ALIAS_NOT_FOUND