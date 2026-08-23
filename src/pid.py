import json

from src.constants import ENCODING, PID_PATH
from src.constants import PID_LOG_PATH
from src.log import setup_logger

logger = setup_logger(__name__, PID_LOG_PATH)

def get_pid():
    try:
        with open(PID_PATH, 'r', encoding=ENCODING) as f:
            result = json.load(f)

    except (OSError, json.JSONDecodeError):
        logger.debug('Not PID found in file')
        return []
    else:
        if not isinstance(result, list):
            result = [result]
        logger.debug(f'PID found in file: {result}')
        return result

def add_pid(pid):
    all_pid = get_pid()
    if pid not in all_pid:
        all_pid.append(pid)
        with open(PID_PATH, 'w', encoding=ENCODING) as f:
            json.dump(all_pid, f)
        logger.debug(f'PID added: {pid}')
    else:
        logger.debug(f'PID not added: {pid} - already exists')

def remove_pid(pid):
    pid = str(pid)
    all_pid = get_pid()
    if pid in all_pid:
        all_pid.remove(pid)
        with open(PID_PATH, 'w', encoding=ENCODING) as f:
            json.dump(all_pid, f)
        logger.debug(f'PID removed: {pid}')
    else:
        logger.debug(f'PID not added: {pid} - already exists')