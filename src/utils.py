# divide into separate files (time_utils.py, etc) if things got messy

from src.sentinels import SENTINELS

def format_ms(ms):
    if ms is None:
        return '--:--:--'
    else:
        ms = int(ms)
        if ms == -1:
            return '--:--:--'
        if ms == 0:
            return '00:00:00'
        else:
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