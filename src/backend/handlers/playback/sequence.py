import random

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from .helpers import (
    get_current_songs, 
    switch_song, 
    switch_shuffle, 
    replay_song, 
    del_current_pos
    )

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def list_(ctx, request):
    return gen_response.Success('obtained current playlist', get_current_songs(ctx))    

def shuffle(ctx, request):
    ctx.playback.shuffle = not ctx.playback.shuffle
    logger.info(f'Shuffle set to {ctx.playback.shuffle}')
    if ctx.playback.shuffle and ctx.playback.current_song_info is not None:
        random.shuffle(ctx.playback.shuffle_order)

    mode = {True: 'on', False: 'off'}[ctx.playback.shuffle]
    return gen_response.Success(f"shuffle mode turned {mode}")

def loop(ctx, request):
    ctx.playback.loop = not ctx.playback.loop
    mode = {True: 'on', False: 'off'}[ctx.playback.loop]
    return gen_response.Success(f'loop mode turned {mode}')

def dice(ctx, request):
    if ctx.playback.current_song_info is None:
        return gen_response.PlayerEmpty('switch to a random song in current playlist')
    elif len(ctx.playback.current_song_info) == 1:
        return gen_response.Failed('can not switch to a random song because there is only one song in current playlist ')
    else:
        pool = list(range(len(ctx.playback.current_song_info)))
        pool.remove(ctx.playback.current_song_num)
        num = random.choice(pool)
        result = ctx.player.load_number(num)
    
        if result is SENTINELS.SUCCESS:
            ctx.playback.set_current_num(ctx.player.number)
    
        return {
            SENTINELS.SUCCESS: gen_response.Success(f'diced to the {num+1}nd song in current playlist: {ctx.playback.get_current_display_name()}'),
            SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty(f'switch to the {num+1}nd song in current playlist'),
            SENTINELS.VLC_ERROR: gen_response.VLCError(f'switch to the {num+1}nd song in current playlist'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout(f'switch to the {num+1}nd song in current playlist'),
        }[result]

def switch(ctx, request):
    num = request['number']
    if num == 0:
        return switch_song(ctx, 0)
    elif num < 0:
        return switch_song(ctx, num)
    else:
        return switch_song(ctx, num-1)

def prev(ctx, request):
    if ctx.playback.shuffle:
        result = ctx.player.load_number(switch_shuffle(ctx, -1))
    else:
        result = ctx.player.switch_prev()
    
    if result is SENTINELS.SUCCESS:
        ctx.playback.set_current_num(ctx.player.number)
    
    response = {
        SENTINELS.SUCCESS: gen_response.Success(f'switched to previous song: {ctx.playback.get_current_display_name()}'),
        SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty('switch to previous song'),
        SENTINELS.VLC_ERROR: gen_response.VLCError('switch to previous song'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('switch to previous song')
    }[result]
    if result is SENTINELS.SUCCESS:
        response += replay_song(ctx)

    return response

def next_(ctx, request):
    on_end = request['on_end']
    if on_end:
        del_current_pos(ctx)

    if on_end and ctx.playback.loop:
        result = ctx.player.load_number(ctx.player.number)
        return {
            SENTINELS.SUCCESS: gen_response.Success('replayed current song'),
            SENTINELS.VLC_ERROR: gen_response.VLCError('replayed current song'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('replayed current song'),
        }[result]
    else:
        if ctx.playback.shuffle:
            result = ctx.player.load_number(switch_shuffle(ctx, 1))
        else:
            result = ctx.player.switch_next()

        if result is SENTINELS.SUCCESS:
            ctx.playback.set_current_num(ctx.player.number)

        response = {
            SENTINELS.SUCCESS: gen_response.Success(f'switched to next song: {ctx.playback.get_current_display_name()}'),
            SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty('switch to next song'),
            SENTINELS.VLC_ERROR: gen_response.VLCError('switch to next song'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('switch to next song')
        }[result]
        if result is SENTINELS.SUCCESS:
            response += replay_song(ctx)

        return response