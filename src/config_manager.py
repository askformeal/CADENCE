from src.config import CONFIG
from src.constants import CONFIG_SCHEME, CONFIG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from src.utils import open_file

class ConfigManager:

    def get_all_option_info(self):
        info = []
        failed = []
        for name in CONFIG_SCHEME.keys():
            option_response = self.get_option_info(name)
            if option_response.ok():
                info.append(option_response.attachment)
            else:
                failed.append(option_response) # not really possible, but who the fuck knows

        return gen_response.BatchAuto('option information obtained', len(failed), len(CONFIG_SCHEME.keys()), attachment=info, failed=failed)

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

            response = gen_response.Success(f'Got value of {name}', {'name': name, 'value': value, 'source': source, 'default': default, 'description': description})

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

    def open_config_file(self):
        result = open_file(CONFIG_PATH)
        if result is SENTINELS.SUCCESS:
            response = gen_response.Success(f'file opened')
        elif result is SENTINELS.FILE_IO_FAILED:
            result = CONFIG.set_file({})
            if result is SENTINELS.SUCCESS:
                response = self.open_config_file()
            elif result is SENTINELS.FILE_IO_FAILED:
                response = gen_response.Failed('failed to created empty configure file')

        elif result is SENTINELS.NO_OPENER:
            response = gen_response.Failed('can not find a method to open file on this platform')

        return response

    def get_path(self):
        return gen_response.Success('Got configure file path', str(CONFIG_PATH)) # This is absolutely necessary

CONFIG_MANAGER = ConfigManager()