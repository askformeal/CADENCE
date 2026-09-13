from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from .helpers import get_status, open_song, play_all_songs, stop_player

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def status(ctx, request):
    return gen_response.Success('status obtained', get_status(ctx))

def open(ctx, request):
    song = request['song']
    cwd = request.get('cwd', None)
    return open_song(ctx, song, cwd)

def play_all(ctx, request):
    return play_all_songs(ctx)

def load_last(ctx, request):
    is_all = ctx.database.get_setting('last_is_all')
    song = ctx.database.get_setting('last_song')
    last_cwd = ctx.database.get_setting('last_cwd')

    if is_all == '1':
        response = play_all_songs(ctx)
    else:
        if song in (SENTINELS.SETTING_NOT_FOUND, None):
            response = gen_response.Failed('No last song to open')
        else:
            response = open_song(ctx, song, last_cwd)

    ctx.playback.update_lyric(force=True)
    logger.debug(response.msg)
    return response

def stop(ctx, request):
    return stop_player(ctx)

def pause(ctx, request):
    result = ctx.player.pause()
    return {
        SENTINELS.SUCCESS: gen_response.Success('player paused'),
        SENTINELS.INVALID_PLAYER_STATE: gen_response.Failed('can not pause player because player is not playing'),
        SENTINELS.VLC_ERROR: gen_response.VLCError('pause player'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('pause player')
    }[result]

def resume(ctx, request):
    result = ctx.player.resume()
    return {
        SENTINELS.SUCCESS: gen_response.Success('player resumed'),
        SENTINELS.INVALID_PLAYER_STATE: gen_response.Failed('can not resume player because player is not paused'),
        SENTINELS.VLC_ERROR: gen_response.VLCError('resume player'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('resume player')
    }[result]

def toggle(ctx, request):
    result = ctx.player.toggle()
    return {
        SENTINELS.SUCCESS: gen_response.Success('player toggled'),
        SENTINELS.INVALID_PLAYER_STATE: gen_response.NotPlayingPaused('toggle player'),
        SENTINELS.VLC_ERROR: gen_response.VLCError('toggle player'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('toggle player')
    }[result]

def volume(ctx, request):
    volume = request['volume']
    if volume.startswith(('+', '-')):
        try:
            step = int(volume[1:])
        except ValueError:
            return gen_response.Failed(f'invalid increase/decrease volume: {volume}')
        else:
            if volume.startswith('-'):
                step = -step
            target_vol = ctx.player.volume + step
            target_vol = max(min(target_vol, 100), 0)
            ctx.player.set_volume(target_vol)
            return gen_response.Success(f'set volume to {ctx.player.volume}%')
    else:
        try:
            volume = int(volume)
        except ValueError:
            return gen_response.Failed(f'invalid volume: {volume}')
        else:
            if volume < 0:
                return gen_response.PercentageTooLow(volume)
            elif volume > 100:
                return gen_response.PercentageTooHigh(volume)
            else:
                ctx.player.set_volume(volume)
                return gen_response.Success(f'set volume to {ctx.player.volume}%')

def mute(ctx, request):
    ctx.player.set_mute(not ctx.player.mute)
    mode = {True: 'on', False: 'off'}[ctx.player.mute]
    return gen_response.Success(f'turned mute mode {mode}')

def lyric(ctx, request):
    ctx.playback.online_lyric = not ctx.playback.online_lyric
    ctx.playback.update_lyric()
    mode = {True: 'on', False: 'off'}[ctx.playback.online_lyric]
    return gen_response.Success(f'online lyric mode turned {mode}')

def set_offset_overlay(ctx, request):
    offset = request['offset']
    if request['autoincrement']:
        ctx.playback.offset_overlay += offset
    else:
        ctx.playback.offset_overlay = offset
    ctx.playback.update_lyric()
    return gen_response.Success(f'lyric offset overlay set to {ctx.playback.offset_overlay}')
    