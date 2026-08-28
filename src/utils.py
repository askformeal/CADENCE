# divide into separate files (time_utils.py, etc) if things got messy
import os
import math
import shutil
import subprocess
from pathlib import Path
import re
import sys
from typing import Literal
from wcwidth import wcswidth

from src.constants import WINDOWS_ILLEGAL, WINDOWS_RESERVED, BOX_STYLES
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

def box(text: str, l_pad=0, r_pad=0, style='ascii'):
    style = str(style)

    upper_left, upper_right, lower_left, lower_right, vertical, horizontal = BOX_STYLES[style]
    
    lines = text.split('\n')
    max_len = max(map(wcswidth, lines))

    l_space = ' ' * l_pad
    r_space = ' ' * r_pad

    result = [
        f"{upper_left}{horizontal * (max_len + l_pad + r_pad + 4)}{upper_right}",
        ]

    for line in lines:
        pad = ' ' * (max_len - wcswidth(line))
        result.append(f'{vertical}{l_space}  {line}{pad}  {r_space}{vertical}')

    result.append(f"{lower_left}{horizontal * (max_len + l_pad + r_pad + 4)}{lower_right}")

    return '\n'.join(result)

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

def count_dict(obj):
    if not isinstance(obj, dict):
        return 1
    else:
        total = 0
        for value in obj.values():
            total += count_dict(value)
        return total

def open_file(path):
    if Path(path).is_file():
        if sys.platform == 'win32':
            os.startfile(path)
            return SENTINELS.SUCCESS
        else:
            if sys.platform == 'darwin':
                opener = shutil.which('open')
            else:
                opener = shutil.which('xdg-open')
            if opener is None:
                return SENTINELS.NO_OPENER
            else:
                subprocess.run([opener, path])
                return SENTINELS.SUCCESS
    else:
        return SENTINELS.FILE_IO_FAILED

def center(text, width):
    l_pad = ' ' * math.ceil((width - wcswidth(text)) / 2)
    r_pad = ' ' * math.floor((width - wcswidth(text)) / 2)
    return f'{l_pad}{text}{r_pad}'

def align(width, left='', right=''):
    l_len = wcswidth(left)
    r_len = wcswidth(right)
    if l_len + r_len > width:
        return f'{left}{right}'
    else:
        return f'{left}{' '*(width-l_len-r_len)}{right}'
    
def progress_bar(progress, length):
    progress = round(progress)
    return f"{'█'*progress}{'░'*(length-progress)}"