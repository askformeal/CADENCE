from io import BytesIO

from PIL import Image

from .logger import logger
from src.constants.backend import MAX_COVER_SIDE, COVER_QUALITY
from src.utils.misc import hash_bytes
from src.utils.file_extract import extract_cover

class CoverMixin:
    def __init__(self):
        self.cover_path = None
        self.cover_hash = None
        self.cover = None

    def update_cover(self):
        if self.current_song_info is not None: 
            # since Monica asked so kindly: yes, cover will remain as the one of the last song when current_song_info become None
            path = self.get_playing_info().get('path', None)
            if self.cover_path != path:
                self.cover_path = path
                self.cover = extract_cover(path)
                if self.cover is None:
                    self.cover_hash = None
                else:
                    try:
                        image = Image.open(BytesIO(self.cover))
                        image.thumbnail((MAX_COVER_SIDE, MAX_COVER_SIDE), Image.Resampling.LANCZOS)
                        buffer = BytesIO()
                        image.convert('RGB').save(
                            buffer, format='JPEG', 
                            quality=COVER_QUALITY, 
                            optimize=True)
                    except (OSError, Image.DecompressionBombError) as e:
                        logger.warning(f'Failed to process cover of \"{path}\": {e}')
                        self.cover = None
                        self.cover_hash = None
                    else:
                        self.cover = buffer.getvalue()
                        self.cover_hash = hash_bytes(self.cover)
