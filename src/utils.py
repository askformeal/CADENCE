# divide into separate files (time_utils.py, etc) if things got messy
import os
from pathlib import Path
import re
from typing import Literal
from wcwidth import wcswidth

from src.constants import WINDOWS_ILLEGAL, WINDOWS_RESERVED
from src.sentinels import SENTINELS


def format_time(raw_time, unit: Literal['ms', 'sec']='ms'):
    if raw_time is None:
        return '--:--:--'
    else:
        raw_time = int(raw_time)

        if raw_time == -1:
            return '--:--:--'
        elif raw_time == 0:
            return '00:00:00'

        if unit == 'sec':
            ms = raw_time * 1000
        else:
            ms = raw_time

        hours, remain = divmod(ms, 3600000) # 3600000 = 1000 * 60 * 60
        minutes, remain = divmod(remain, 60000) # 60000 = 1000 * 60
        seconds = remain // 1000
        return f'{hours:02}:{minutes:02}:{seconds:02}'
        
def parse_time(time):
    # Technically it can parse things like 999999:9999999:999999 but I decided to count that as a feature
    parts = time.split(':')

    length = len(parts)
    if length > 3:
        return SENTINELS.INVALID_TIME
    else:
        for i in range(length):
            try:
                parts[i] = int(parts[i])
            except ValueError:
                return SENTINELS.INVALID_TIME
            else:
                if parts[i] < 0:
                    return SENTINELS.INVALID_TIME

        parts = [0, 0] + parts
        ms = parts[-1] * 1000 + parts[-2] * 60000 + parts[-3] * 3600000
        return ms

def box(text: str):
    lines = text.split('\n')
    max_len = max(map(wcswidth, lines))

    result = f" {'_' * (max_len + 4)} \n"
    result += f"/  {' ' * max_len}  \\\n"

    for line in lines:
        pad = ' ' * (max_len - wcswidth(line))
        result += f'|  {line}{pad}  |\n'

    result += f"\\{'_' * (max_len + 4)}/\n"

    return result

def verify_path_format(raw: str):
    if len(raw.strip()) == 0 or '\x00' in raw:
        return False
    elif os.name == 'nt':
        if re.match(r'^[a-zA-Z]:', raw):
            body = raw[2:]
        else:
            body = raw

        if re.search(WINDOWS_ILLEGAL, body) is not None:
            return False
        else:
            filename = Path(body).name.split('.')[0].upper()
            if filename in WINDOWS_RESERVED:
                return False
            else:
                return True
    else:
        return True