from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.config_manager import CONFIG_MANAGER

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def list_(ctx, request):
    return CONFIG_MANAGER.get_all_option_info()

def show(ctx, request):
    option = request['option']
    return CONFIG_MANAGER.get_option_info(option)

def set_(ctx, request):
    option = request['option']
    value = request['value']
    overwrite_corrupt = request['overwrite_corrupt']
    return CONFIG_MANAGER.set_option_value(option, value, overwrite_corrupt=overwrite_corrupt)

def unset(ctx, request):
    option = request['option']
    return CONFIG_MANAGER.unset_option(option)

def open_(ctx, request):
    return CONFIG_MANAGER.open_config_file()

def path(ctx, request):
    return CONFIG_MANAGER.get_path()