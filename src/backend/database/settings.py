from .logger import logger
from src.sentinels import SENTINELS

class SettingsMixin:
    def setting_exists(self, key):
        row = self.execute('SELECT 1 FROM settings WHERE key = ?', key).fetchone()
        if row is None:
            result = False
        else:
            result = True
        logger.debug(f'Checked the existence of setting {key}, result: {result}')
        return result

    def get_setting(self, key):
        row = self.execute('SELECT value FROM settings WHERE key = ?', key).fetchone()
        if row is None:
            logger.debug(f'Failed to get the value of setting \"{key}\" because it does not exist')
            return SENTINELS.SETTING_NOT_FOUND
        else:
            logger.debug(f'Got the value of setting \"{key}\": {row['value']}')
            return row['value']

    def set_setting(self, key, value):
        if self.setting_exists(key):
            self.execute('UPDATE settings SET value = ? WHERE key = ?', value, key)
            logger.debug(f'Updated setting \"{key}\" to \"{value}\"')
        else:
            self.execute('INSERT INTO settings(key, value) VALUES (?, ?)', key, value)
            logger.debug(f'Created setting \"{key}\" with value \"{value}\"')