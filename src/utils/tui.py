import math
import re

from wcwidth import wcswidth
from src.constants import BOX_STYLES

ESCAPE_PATTERN = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

def strlen(text):
    return wcswidth(ESCAPE_PATTERN.sub('', text))

def box(*texts: str, l_pad=2, r_pad=2, style='ascii'):
    style = str(style)

    upper_left, upper_right, lower_left, lower_right, vertical, horizontal, t_down, t_up = BOX_STYLES[style]

    l_space = ' ' * l_pad
    r_space = ' ' * r_pad

    lines = list(map(lambda x:x.splitlines(), texts))

    max_lines = max(map(len, lines))

    max_width = []
    for text_lines in lines:
        max_width.append(max(map(strlen, text_lines)))

    top_line = ''
    for length in max_width:
        top_line += f'{horizontal * (length + l_pad + r_pad)}{t_down}'
    top_line = f'{upper_left}{top_line[:-1]}{upper_right}'

    bottom_line = ''
    for length in max_width:
        bottom_line += f'{horizontal * (length + l_pad + r_pad)}{t_up}'
    bottom_line = f'{lower_left}{bottom_line[:-1]}{lower_right}'

    middle_lines = []
    for i in range(max_lines):
        line = []
        for j, text_lines in enumerate(lines):
            if i < len(text_lines):
                text = text_lines[i]
            else:
                text = ''
            pad = ' ' * (max_width[j] - strlen(text))
            line.append(f'{text}{pad}')

        line = f'{r_space}{vertical}{l_space}'.join(line)
        middle_lines.append(f'{vertical}{l_space}{line}{r_space}{vertical}')

    return '\n'.join((top_line, *middle_lines, bottom_line))


def center(text, width):
    result = []
    for line in text.splitlines():
        l_pad = ' ' * math.ceil((width - strlen(line)) / 2)
        r_pad = ' ' * math.floor((width - strlen(line)) / 2)
        result.append(f'{l_pad}{line}{r_pad}')
    return '\n'.join(result)

def align(width, left='', right=''):
    l_len = strlen(left)
    r_len = strlen(right)
    if l_len + r_len > width:
        return f'{left}{right}'
    else:
        return f'{left}{' '*(width-l_len-r_len)}{right}'
    
def progress_bar(progress, length):
    progress = min(max(round(progress), 0), length)
    return f"{'█'*progress}{'░'*(length-progress)}"

def wrap_text(text, max_len):
    lines = ['']
    words = text.split(' ')
    for word in words:
        if strlen(lines[-1]) + strlen(word) + 1 <= max_len:
            if lines[-1] != '':
                lines[-1] += ' '
            lines[-1] += word
        else:
            lines.append(word)
    return '\n'.join(lines)

def window_list(lines, window_len, selected, current=None, filter='', newline_selected=False, mark_unshown=True, left_align=True, end_of_line_char=''):
    from .misc import squeeze
    result = []

    length = len(lines)
    selected = squeeze(selected, length-1)

    upper_index = math.ceil(selected - window_len / 2)
    lower_index = math.ceil(selected + window_len / 2)

    if upper_index < 0:
        lower_index -= upper_index
        upper_index = 0

    if lower_index >= length:
        upper_index -= lower_index - length + 1
        lower_index = length - 1

    max_len = max(map(strlen, lines)) + 10

    for i, line in enumerate(lines):
        line = line.strip()
        if filter != '':
            start = line.lower().find(filter.lower())
            if start != -1:
                end = start + len(filter)
                line = f'{line[:start]}[{line[start:end]}]{line[end:]}'
        if i == selected:
            line = f'-[ {line} ]-'
            line = line.replace('\n', ' ]-\n-[ ')

        if i == current:
            line = f'> {line} <'

        if i == selected and newline_selected:
            line = f'\n{line}\n'

        if i in range(upper_index, lower_index+1):
            result.append(line)

    for i, line in enumerate(result):
        if left_align:
            pad = ' ' * (max_len - strlen(line))
        else:
            pad = ''
        result[i] = f'{line}{pad}{end_of_line_char}'

    if mark_unshown:
        above_mark = [align(max_len, right=f'{max(upper_index, 0)} ↑ ')]
        below_mark = [align(max_len, right=f'{len(lines)-lower_index-1} ↓ ')]

        result = above_mark + result + below_mark

    return result