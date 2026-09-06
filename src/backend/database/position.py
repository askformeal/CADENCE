from .logger import logger
from src.sentinels import SENTINELS

class PosMixin:
    def pos_memorized(self, path, log=True):
        # if the pos of a path is memorized
        row = self.execute('SELECT 1 FROM positions WHERE path = ?', path).fetchone()
        if row is not None:
            result = True
        else:
            result = False
        if log:
            logger.debug(f'Check if position of {path} is memorized, result {result}')
        return result

    def get_pos(self, path):
        # get the memorized pos of a path
        row = self.execute('SELECT position FROM positions WHERE path = ?', path).fetchone()
        if row is not None:
            logger.debug(f'Got position of {path}: {row['position']}ms')
            return row['position']
        else:
            logger.debug(f'Failed to get position of {path} because it is not memorized')
            return SENTINELS.POS_NOT_FOUND

    def set_pos(self, path, pos, log=True):
        # memorize the pos of a path
        if self.pos_memorized(path, log=log):
            self.execute('UPDATE positions SET position = ? WHERE path = ?', pos, path)
            msg = f'Updated memorized position of {path} to {pos}ms'
        else:
            msg = f'Create memorized position of {path} as {pos}ms'
            self.execute('INSERT INTO positions(path, position) VALUES (?, ?)', path, pos)
        if log:
            logger.debug(msg)
        self.connection.commit()
        return SENTINELS.SUCCESS

    def del_pos(self, path):
        # delete the memorized pos of a path
        if self.pos_memorized(path):
            self.execute('DELETE FROM positions WHERE path = ?', path)
            logger.debug(f'Deleted the position of {path} from memory')
            return SENTINELS.SUCCESS
        else:
            return SENTINELS.POS_NOT_FOUND