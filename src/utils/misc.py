# TODO divide into separate files (time_utils.py, etc). things are getting messy
import os
import shutil
import subprocess
from pathlib import Path
import re
import sys
import base64
import hashlib

from src.constants.misc import WINDOWS_ILLEGAL, WINDOWS_RESERVED, AUDIO_EXTENSIONS
from src.sentinels import SENTINELS

def squeeze(number, highest, lowest=0):
    if number > highest:
        number = highest
    elif number < lowest:
        number = lowest

    return number

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

def hex_color_to_dec(color):
    color = color.replace('#', '0x')
    num = int(color, 16)
    return num

def sort_songs(info):
    return sorted(info, key=lambda x: Path(x['path']).name.lower())

def get_song_display_name( info):
    name = info.get('name', None)
    if name is None:
        name = info.get('path', None)
        if name is not None:
            name = Path(name).stem
    return name

def shallow_scan(directory):
    paths = []
    for path in Path(directory).iterdir():
        if path.suffix.lower() in AUDIO_EXTENSIONS and path.is_file():
            paths.append(str(path.resolve()))
    return paths

def recurse_scan(directory):
    paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            path = Path(root) / file
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                paths.append(str(path.resolve()))
    return paths

def bytes2base64(data):
    return base64.b64encode(data).decode('ascii')

def base642bytes(data):
    return base64.b64decode(data)

def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()
