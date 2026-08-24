import tomllib
import tomli_w

from src.log import setup_logger

from src.constants import CONFIG_PATH, CONFIG_SCHEME, READABLE_TYPE_NAMES
from src.constants import CONFIG_LOG_PATH
from src.sentinels import SENTINELS
from src.utils import count_dict

logger = setup_logger(__name__, CONFIG_LOG_PATH)

class Config:
    def __init__(self):
        logger.debug(f'{__name__} initiated')

    def load_file(self):
        try:
            with open(CONFIG_PATH, 'rb') as f:
                file_config = tomllib.load(f)

        except OSError as e:
            if isinstance(e, FileNotFoundError):
                logger.debug('Configure file not found')
            else:
                logger.warning(f'Failed to access configure file: {e}')
            return SENTINELS.FILE_IO_FAILED

        except tomllib.TOMLDecodeError:
            logger.warning(f'Configure file invalid')
            return SENTINELS.INVALID_CONFIG_FILE

        else:
            logger.debug(f'{count_dict(file_config)} options found in file')
            return file_config

    def set_file(self, file_config):
        try:
            with open(CONFIG_PATH, 'wb') as f:
                tomli_w.dump(file_config, f)

        except OSError as e:
            logger.warning(f'Failed to write into configure file: {e}')
            return SENTINELS.FILE_IO_FAILED

        else:
            return SENTINELS.SUCCESS

    def get_option(self, name):
        if name not in CONFIG_SCHEME.keys():
            logger.warning(f'Tried to get an unknown option \"{name}\". A Sentinel object will be returned and will most likely cause an error')
            return SENTINELS.UNKNOWN_OPTION, None
        
        else:
            file_config = self.load_file()
            if file_config in (SENTINELS.INVALID_CONFIG_FILE, SENTINELS.FILE_IO_FAILED):
                file_config = {}
            
            section = CONFIG_SCHEME[name]['section']
            option_type = CONFIG_SCHEME[name]['type']
            default = CONFIG_SCHEME[name]['default']

            value = default
            source = SENTINELS.FROM_DEFAULT

            if section is SENTINELS.ROOT_SECTION:
                parent = file_config
            else:
                parent = file_config.get(section, {})
            
            file_value = parent.get(name, SENTINELS.OPTION_NOT_FOUND)

            if file_value is not SENTINELS.OPTION_NOT_FOUND:
                try:
                    file_value = option_type(file_value)
                except ValueError:
                    logger.warning(f"the value of \"{name}\" option must be a {READABLE_TYPE_NAMES[option_type]} value "
                                   f"but a value of type \"{type(value).__name__}\" was read from file instead. Default value of {default} will be used")
                else:
                    value = file_value
                    source = SENTINELS.FROM_FILE

            return value, source

    def set_option(self, name, value, overwrite_corrupt=False): 
        # overwrite_corrupt: overwrite invalid config file
        if name not in CONFIG_SCHEME.keys():
            logger.debug(f'Tried to set an unknown option \"{name}\". Setting will be cancelled')
            return SENTINELS.UNKNOWN_OPTION

        else:
            file_config = self.load_file()
            if file_config is SENTINELS.INVALID_CONFIG_FILE:
                if overwrite_corrupt:
                    file_config = {}
                else:
                    return SENTINELS.INVALID_CONFIG_FILE

            elif file_config is SENTINELS.FILE_IO_FAILED:
                file_config = {}

            section = CONFIG_SCHEME[name]['section']
            option_type = CONFIG_SCHEME[name]['type']

            try:
                value = option_type(value)
            except ValueError:
                    logger.warning(f"the value of \"{name}\" option must be a {READABLE_TYPE_NAMES[option_type]} value "
                                f"but a value of type \"{type(value).__name__}\" was provided instead. Setting cancelled")
                    return SENTINELS.INVALID_OPTION_VALUE
            else:
                if section is SENTINELS.ROOT_SECTION:
                    file_config[name] = value
                else:
                    file_config[section] = file_config.get(section, {})
                    file_config[section][name] = value

                return self.set_file(file_config)

    def unset_option(self, name):
        if name not in CONFIG_SCHEME.keys():
            logger.debug(f'Tried to unset an unknown option \"{name}\". Unsetting will be cancelled')
            return SENTINELS.UNKNOWN_OPTION
        else:
            file_config = self.load_file()
            if file_config is SENTINELS.INVALID_CONFIG_FILE:
                return SENTINELS.INVALID_CONFIG_FILE

            elif file_config is SENTINELS.FILE_IO_FAILED:
                return SENTINELS.FILE_IO_FAILED
            
            else:
                section = CONFIG_SCHEME[name]['section']
                
                if section is SENTINELS.ROOT_SECTION:
                    if file_config.get(name, None) is None:
                        return SENTINELS.OPTION_NOT_FOUND
                    else:
                        del file_config[name]
                        return self.set_file(file_config)
                else:
                    if file_config.get(section, {}).get(name, None) is None:
                        return SENTINELS.OPTION_NOT_FOUND
                    else:
                        del file_config[section][name]
                        return self.set_file(file_config)

    def __getattr__(self, name):
        return self.get_option(name)[0]
    
    def __setattr__(self, name, value):
        if name in CONFIG_SCHEME.keys():
            return self.set_option(name, value)
        else:
            object.__setattr__(self, name, value)

CONFIG = Config()