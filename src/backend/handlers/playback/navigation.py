from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from src.utils.time_ import parse_time
from .helpers import jump_to_pos, replay_song, del_current_pos

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def seek(ctx, request):
    raw_time = request['time']
    if raw_time.startswith(('+', '-')):
        step = parse_time(raw_time[1:])
        if step is SENTINELS.INVALID_TIME:
            return gen_response.Failed(f'invalid forward/backward time: {raw_time}')
        else:
            if raw_time.startswith('-'):
                step = -step
    
            progress = ctx.player.get_progress()
            length = progress['length']
            current_pos = progress['time']
    
            pos = current_pos + step
            if length > 0:
                pos = min(pos, length)
            pos = max(pos, 0)
            return jump_to_pos(ctx, pos)
    else:   
        pos = parse_time(raw_time)
        if pos is SENTINELS.INVALID_TIME:
            return gen_response.Failed(f'invalid time: {raw_time}')
        else:
            return jump_to_pos(ctx, pos)

def jump(ctx, request):
    percent = request['progress']
    if percent < 0:
        return gen_response.PercentageTooLow(percent)
    elif percent > 100:
        return gen_response.PercentageTooHigh(percent)
    else:
        length = ctx.player.get_progress()['length']
        if length == -1:
            return gen_response.NotPlayingPaused('jump to progress')
        else:
            pos = length * (percent / 100)
            return jump_to_pos(ctx, pos)

def replay(ctx, request):
    response = replay_song(ctx)
    if response.ok():
        del_current_pos(ctx)
    return response