# TODO divide into separate files (time_utils.py, etc). things are getting messy
import os
import shutil
import subprocess
from pathlib import Path
import re
import sys
import mutagen

from src.log import setup_logger
from src.constants import UTIL_LOG_PATH
from src.constants import WINDOWS_ILLEGAL, WINDOWS_RESERVED, FILE_META, AUDIO_EXTENSIONS
from src.sentinels import SENTINELS

logger = setup_logger(__name__, UTIL_LOG_PATH)

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

def extract_file_meta(path):
    try:
        file = mutagen.File(path, easy=True)
    except (OSError, mutagen.MutagenError):
        logger.debug(f'Failed to extract metadata from {path} because it is not accessible')
        return {}
    else:
        tags = {}
        if file is not None:
            for file_tag, meta in FILE_META.items():
                tags[meta] = file.get(file_tag, [None])[0]
                if tags[meta] == '':
                    tags[meta] = None

            tags['duration'] = getattr(file.info, 'length', None)
            tags['bitrate'] = getattr(file.info, 'bitrate', None)
            tags['sample_rate'] = getattr(file.info, 'sample_rate', None)
            tags['channels'] = getattr(file.info, 'channels', None)

            if tags['duration'] is not None:
                tags['duration'] = int(tags['duration'] * 1000)

            logger.debug(f'Extracted metadata from {path}: {tags}')
            return tags
        else:
            logger.debug(f'Failed to extract metadata from {path} because there is no metadata in the file')
            return {}

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
