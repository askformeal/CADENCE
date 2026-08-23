import logging

from src.constants import FILE_LOG_LEVEL, CONSOLE_LOG_LEVEL, ENCODING

class FlushFileHandler(logging.FileHandler):
    def __init__(self, filename, mode = "a", encoding = None, delay = False, errors = None):
        super().__init__(filename, mode, encoding, delay, errors)

    def emit(self, record):
        super().emit(record)
        self.flush()

def setup_logger(name, path) -> logging.Logger:
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        format=logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")

        console = logging.StreamHandler()
        console.setLevel(CONSOLE_LOG_LEVEL)
        console.setFormatter(format)

        file = FlushFileHandler(path, encoding=ENCODING)
        file.setLevel(FILE_LOG_LEVEL)
        file.setFormatter(format)

        logger.addHandler(console)
        logger.addHandler(file)
        logger.setLevel(FILE_LOG_LEVEL)

    return logger