from pathlib import Path
import base64

import mutagen
import mutagen.flac
import mutagen.id3
import mutagen.mp4
import mutagen.ogg

from .logger import logger

from src.constants import FILE_META, COVER_NAMES, COVER_EXTENSIONS

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

def _pick_front(pictures):
    if len(pictures) == 0:
        return None
    else:
        for picture in pictures:
            if picture.type == mutagen.id3.PictureType.COVER_FRONT:
                return picture.data
            
        return pictures[0].data


def extract_cover(path):
    path = Path(path)
    try:
        file = mutagen.File(path)
    except (OSError, mutagen.MutagenError):
        logger.debug(f'Failed to extract album cover from {str(path)} because it is not accessible')
        file = None
    if file is not None and file.tags is not None:
        data = None
        if isinstance(file, mutagen.flac.FLAC):
            pictures = file.pictures
            data = _pick_front(pictures)
            
        elif isinstance(file, mutagen.mp4.MP4):
            cover = file.tags.get('covr')
            if cover is not None and len(cover) > 0:
                data = bytes(cover[0])

        elif isinstance(file.tags, mutagen.id3.ID3):
            frames = file.tags.getall('APIC')
            data = _pick_front(frames)

        elif isinstance(file, mutagen.ogg.OggFileType):
            blocks = file.tags.get('metadata_block_picture', [])
            pictures = list(map(lambda b: mutagen.flac.Picture(base64.b64decode(b)), blocks))
            data = _pick_front(pictures)

        if data is not None:
            return data

    try:
        entries = sorted(path.parent.iterdir())
    except OSError:
        entries = []
    for entry in entries:
        if (
            entry.suffix.lower() in COVER_EXTENSIONS
            and entry.stem.lower() in COVER_NAMES
        ):
            try:
                with open(entry, 'rb') as f:
                    data = f.read()
            except OSError:
                return None
            else:
                return data
    return None