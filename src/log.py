import logging
import os
from pathlib import Path

from src.constants import (
    FILE_LOG_LEVEL, 
    CONSOLE_LOG_LEVEL, 
    ENCODING, 
    LOG_MAX_LENGTH,
    LOG_FILE_MAX_BYTES
    )

class TruncateFilter(logging.Filter):
    def __init__(self, max_len):
        super().__init__()
        self.max_len = max_len

    def filter(self, record):
        message = record.getMessage()
        if len(message) > self.max_len:
            record.msg = f'{message[:self.max_len]}... (truncated, {len(message)} chars in total)'
            record.args = ()
        return True

class RotatingFlushFileHandler(logging.FileHandler):
    def __init__(self, filename, max_bytes, mode = "a", encoding = None, delay = False, errors = None):
        super().__init__(filename, mode, encoding, delay, errors)
        self.path = Path(self.baseFilename)
        self.max_bytes = max_bytes

    def emit(self, record):
        try:
            if self.path.stat().st_size > self.max_bytes:
                self.stream.seek(0)
                self.stream.truncate()
        except OSError:
            ...
        super().emit(record)
        self.flush()

def setup_logger(name, path, add_console=True) -> logging.Logger:
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        format=logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

        console = logging.StreamHandler()
        console.setLevel(CONSOLE_LOG_LEVEL)
        console.setFormatter(format)

        file = RotatingFlushFileHandler(
            path, 
            max_bytes=LOG_FILE_MAX_BYTES, 
            encoding=ENCODING
            )
        file.setLevel(FILE_LOG_LEVEL)
        file.setFormatter(format)

        if add_console:
            logger.addHandler(console)
        logger.addHandler(file)
        logger.addFilter(TruncateFilter(LOG_MAX_LENGTH))
        logger.setLevel(FILE_LOG_LEVEL)

    return logger