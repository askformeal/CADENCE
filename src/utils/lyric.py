import re

from src.constants import ENCODING_CHAIN
from src.sentinels import SENTINELS

def parse_lyric(path, content=None):
    timestamp = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\]')
    if content is None:
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
        return SENTINELS.EMPTY_LYRIC
    else:
        if pos < lyric[0][0]:
            return SENTINELS.BEFORE_FIRST_LYRIC
        elif pos >= lyric[-1][0]:
            return len(lyric)-1
        else:
            for i, line in enumerate(lyric[:-1]):
                if pos >= line[0] and pos < lyric[i+1][0]:
                    return i