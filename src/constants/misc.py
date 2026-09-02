from src.types import CONVERTER, IterType

import logging

ENCODING = 'utf-8'
ENCODING_CHAIN = ('utf-8', 'gb18030', 'big5', 'shift_jis', 'utf-16')

LOG_MAX_LENGTH = 500

FILE_LOG_LEVEL = logging.DEBUG
CONSOLE_LOG_LEVEL = logging.INFO
SILENT_LOG_LEVEL = logging.WARNING

READABLE_TYPE_NAMES = {
    str: 'string',
    int: 'integer',
    bool: 'boolean',
    IterType: 'list or tuple',
    CONVERTER.boolean: 'boolean',
    CONVERTER.port: 'network port',
    CONVERTER.pos_int: 'positive integer',
    CONVERTER.timeout: 'positive float',
    CONVERTER.percentage: 'percentage number'
}

MIN_TIMEOUT = 0.01

WINDOWS_ILLEGAL = r'[<>:"|?*]'
WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL',
                    'COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9',
                    'LPT1','LPT2','LPT3','LPT4','LPT5','LPT6','LPT7','LPT8','LPT9'}

BOX_STYLES = {
    'ascii': ('/', '\\', '\\', '/', '|', '=', '+', '+'),
    'at': ('@', '@', '@', '@', '|', '=', '+', '+'),
    'rounded': ('╭', '╮', '╰', '╯', '│', '─', '┬', '┴'),
    'square': ('┌', '┐', '└', '┘', '│', '─', '┬', '┴'),
    'double-corner': ('╔', '╗', '╚', '╝', '│', '─', '┬', '┴'),
    'heavy-corner': ('┏', '┓', '┗', '┛', '│', '─', '┬', '┴'),
    'double': ('╔', '╗', '╚', '╝', '║', '═', '╦', '╩'),
    'heavy': ('┏', '┓', '┗', '┛', '┃', '━', '┳', '┻'),
}