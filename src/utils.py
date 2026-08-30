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

from src.constants import ENCODING, ENCODING_CHAIN, WINDOWS_ILLEGAL, WINDOWS_RESERVED, BOX_STYLES
from src.sentinels import SENTINELS


def squeeze(number, highest, lowest=0):
    if number > highest:
        number = highest
    elif number < lowest:
        number = lowest

    return number

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
        f"{upper_left}{horizontal * (max_len + l_pad + r_pad + 2)}{upper_right}",
        ]

    for line in lines:
        pad = ' ' * (max_len - wcswidth(line))
        result.append(f'{vertical}{l_space} {line}{pad} {r_space}{vertical}')

    result.append(f"{lower_left}{horizontal * (max_len + l_pad + r_pad + 2)}{lower_right}")

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
    result = []
    for line in text.splitlines():
        l_pad = ' ' * math.ceil((width - wcswidth(line)) / 2)
        r_pad = ' ' * math.floor((width - wcswidth(line)) / 2)
        result.append(f'{l_pad}{line}{r_pad}')
    return '\n'.join(result)

def align(width, left='', right=''):
    l_len = wcswidth(left)
    r_len = wcswidth(right)
    if l_len + r_len > width:
        return f'{left}{right}'
    else:
        return f'{left}{' '*(width-l_len-r_len)}{right}'
    
def progress_bar(progress, length):
    progress = min(max(round(progress), 0), length)
    return f"{'█'*progress}{'░'*(length-progress)}"

def wrap_text(text, max_len):
    lines = ['']
    words = text.split(' ')
    for word in words:
        if wcswidth(lines[-1]) + wcswidth(word) + 1 <= max_len:
            if lines[-1] != '':
                lines[-1] += ' '
            lines[-1] += word
        else:
            lines.append(word)
    return '\n'.join(lines)

def window_list(lines, window_len, selected, current=None, filter='', newline_selected=False, mark_unshown=True, left_align=True, end_of_line_char=''):
    result = []

    length = len(lines)
    selected = squeeze(selected, length-1)

    upper_index = math.ceil(selected - window_len / 2)
    lower_index = math.ceil(selected + window_len / 2)

    if upper_index < 0:
        lower_index -= upper_index
        upper_index = 0

    if lower_index >= length:
        upper_index -= lower_index - length + 1
        lower_index = length - 1

    max_len = max(map(wcswidth, lines)) + 10

    for i, line in enumerate(lines):
        if filter != '':
            start = line.lower().find(filter.lower())
            if start != -1:
                end = start + len(filter)
                lines[i] = f'{line[:start]}[{line[start:end]}]{line[end:]}'
        if i == selected:
            lines[i] = f'-[ {lines[i]} ]-'
            lines[i] = lines[i].replace('\n', ' ]-\n-[ ')
            if newline_selected:
                lines[i] = f'\n{lines[i]}\n'
        if i == current:
            lines[i] = f'> {lines[i]} <'

        if i in range(upper_index, lower_index+1):
            result.append(lines[i])

    for i, line in enumerate(result):
        if left_align:
            pad = ' ' * (max_len - wcswidth(line))
        else:
            pad = ''
        result[i] = f'{line}{pad}{end_of_line_char}'

    if mark_unshown:
        above_mark = [align(max_len, right=f'{max(upper_index, 0)} ↑ ')]
        below_mark = [align(max_len, right=f'{len(lines)-lower_index-1} ↓ ')]

        result = above_mark + result + below_mark

    return result

def parse_lyric(path):
    timestamp = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\]')
    for encoding in ENCODING_CHAIN:
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        else:
            break
    else:
        return SENTINELS.FILE_IO_FAILED
    result = []
    lines = content.splitlines()
    for line in lines:
        matches = re.findall(timestamp, line)            
        if len(matches) > 0:
            text = timestamp.sub('', line).strip()
            for minute, second, ms in matches:
                pos = int(minute) * 60000 + int(second) * 1000
                if ms != '':
                    pos += int(ms.ljust(2, '0')) * 10
                if len(result) > 0 and pos == result[-1][0]:
                    result[-1][1] += f'\n{text}'
                else:
                    result.append([pos, text])
                    
    return result

def get_lyric_line(lyric, pos):
    if len(lyric) == 0:
        return None
    else:
        if pos < lyric[0][0]:
            return SENTINELS.BEFORE_FIRST_LYRIC
        elif pos >= lyric[-1][0]:
            return len(lyric)-1
        else:
            for i, line in enumerate(lyric[:-1]):
                if pos >= line[0] and pos < lyric[i+1][0]:
                    return i