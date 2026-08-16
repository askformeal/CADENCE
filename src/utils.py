# divide into separate files (time_utils.py, etc) if things got messy

def format_ms(ms):
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