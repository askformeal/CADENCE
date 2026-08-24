from src.config import CONFIG
from src.constants import CONFIG_SCHEME
from src.sentinels import SENTINELS
from src import gen_response

class ConfigManager:

    def get_option_info(self, name):
        value, source = CONFIG.get_option(name)
        
        if value is SENTINELS.UNKNOWN_OPTION:
            response = gen_response.OptionNotExist(f'get value of {name}')
        else:
            source = {
                SENTINELS.FROM_DEFAULT: 'default value',
                SENTINELS.FROM_FILE: 'configure file'
            }[source]

            default = CONFIG_SCHEME[name]['default']
            description = CONFIG_SCHEME[name]['description']

            response = gen_response.Success(f'Got value of {name}', {'value': value, 'source': source, 'default': default, 'description': description})

        return response

    def set_option_value(self, name, value, overwrite_corrupt=False):
        result = CONFIG.set_option(name, value, overwrite_corrupt=overwrite_corrupt)
        return {
            SENTINELS.SUCCESS: gen_response.Success(f'Set value of {name} to \"{value}\"'),
            SENTINELS.UNKNOWN_OPTION: gen_response.OptionNotExist(f'set value of {name}'),
            SENTINELS.INVALID_CONFIG_FILE: gen_response.Failed(f'can not set value of option because configure file is corrupted. You can try again with the --overwrite-corrupt option to overwrite it'),
            SENTINELS.INVALID_OPTION_VALUE: gen_response.Failed(f'can not set value of option because the provided value is not valid'),
            SENTINELS.FILE_IO_FAILED: gen_response.Failed(f'can not set value of option because failed to write into configure file')
        }[result]

    def unset_option(self, name):
        result = CONFIG.unset_option(name)
        return {
            SENTINELS.SUCCESS: gen_response.Success(f'Unset value of {name}'),
            SENTINELS.UNKNOWN_OPTION: gen_response.OptionNotExist(f'unset value of {name}'),
            SENTINELS.INVALID_CONFIG_FILE: gen_response.Failed(f'can not unset value of option because configure file is corrupted'),
            SENTINELS.OPTION_NOT_FOUND: gen_response.Failed(f'can not unset value of option because it is not set in configure file'),
            SENTINELS.FILE_IO_FAILED: gen_response.Failed(f'can not unset value of option because failed to write into configure file')
        }[result]

CONFIG_MANAGER = ConfigManager()