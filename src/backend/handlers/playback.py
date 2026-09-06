import random
import time
from pathlib import Path
import vlc

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from src.utils import format_time, parse_lyric, parse_time, sort_songs

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def status(ctx, request):
    player_status = {
        vlc.State.Playing: 'playing',
        vlc.State.Paused: 'paused',
        vlc.State.Stopped: 'stopped'
    }.get(ctx.player.player.get_state(), None)
    
    if ctx.playback.current_song_info is None:
        info = {}
        playlist_len = None
        current_num = None
    else:
        info = ctx.playback.get_playing_info()
        playlist_len = len(ctx.playback.current_song_info)
        current_num = ctx.playback.current_song_num
    
    status = {
        'id': info.get('id', None),
        'path': info.get('path', None),
        'name': info.get('name', None),
        'artist': info.get('artist', None),
        'album': info.get('album', None),
        'lyric': info.get('lyric', None),
        'in_library': ctx.playback.current_song_in_lib,
        'player_status': player_status,
        'volume': ctx.player.volume,
        'mute': ctx.player.mute,
        'shuffle': ctx.playback.shuffle,
        'loop': ctx.playback.loop,
        'playlist_len': playlist_len,
        'current_num': current_num,
        'run_time': time.time() - ctx.start_time
    }
    progress = ctx.player.get_progress()
    status['length'] = progress['length']
    status['time'] = progress['time']
    status['dev'] = ctx.dev
    return gen_response.Success('status obtained', status)

def open(ctx, request):
    song = request['song']
    cwd = request.get('cwd', None)
    return _open_song(ctx, song, cwd)

def play_all(ctx, request):
    return _play_all_songs(ctx)

def continue_last(ctx, request):
    is_all = ctx.database.get_setting('last_is_all')
    song = ctx.database.get_setting('last_song')
    last_cwd = ctx.database.get_setting('last_cwd')

    if is_all == '1':
        response = _play_all_songs(ctx)
    else:
        if song in (SENTINELS.SETTING_NOT_FOUND, None):
            response = gen_response.Failed('No last song to open')
        else:
            response = _open_song(ctx, song, last_cwd)

    logger.debug(response.msg)
    return response

def stop(ctx, request):
    return _stop_player(ctx)

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

def list_(ctx, request):
    response = gen_response.Success('obtained current playlist')
    if ctx.playback.current_song_info is not None:
        response.attachment = ctx.playback.current_song_info.copy()
    else:
        response.attachment = []
    return response

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
        return _switch_song(ctx, 0)
    elif num < 0:
        return _switch_song(ctx, num)
    else:
        return _switch_song(ctx, num-1)

def prev(ctx, request):
    if ctx.playback.shuffle:
        result = ctx.player.load_number(_switch_shuffle(ctx, -1))
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
        response += _replay(ctx)

    return response

def next_(ctx, request):
    on_end = request['on_end']
    if on_end:
        _del_current_pos(ctx)

    if on_end and ctx.playback.loop:
        result = ctx.player.load_number(ctx.player.number)
        return {
            SENTINELS.SUCCESS: gen_response.Success('replayed current song'),
            SENTINELS.VLC_ERROR: gen_response.VLCError('replayed current song'),
            SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('replayed current song'),
        }[result]
    else:
        if ctx.playback.shuffle:
            result = ctx.player.load_number(_switch_shuffle(ctx, 1))
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
            response += _replay(ctx)

        return response

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
            return _jump_to_pos(ctx, pos)
    else:   
        pos = parse_time(raw_time)
        if pos is SENTINELS.INVALID_TIME:
            return gen_response.Failed(f'invalid time: {raw_time}')
        else:
            return _jump_to_pos(ctx, pos)

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
            return _jump_to_pos(ctx, pos)

def replay(ctx, request):
    response = _replay(ctx)
    if response.ok():
        _del_current_pos(ctx)
    return response

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
    if ctx.playback.current_song_info is None:
        return gen_response.PlayerEmpty('get lyric of current song')
    else:
        info = ctx.playback.get_playing_info()
        lyric_path = info.get('lyric', None)
        if lyric_path is None:
            return gen_response.LyricNotExist()
        else:
            lyric = parse_lyric(lyric_path)
            if lyric is SENTINELS.FILE_IO_FAILED:
                return gen_response.FileIOFailed('open lyric file', lyric_path)
            else:
                attachment = {'path': lyric_path, 'lyric': lyric}
                return gen_response.Success('lyric of current song obtained', attachment=attachment)



# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _open_song(ctx, song, cwd) -> gen_response.Response:
    from .library.library import get_song, get_playlist_songs

    info_to_set = None
    paths_to_load = None # MUST be a list!!!
    playlist_id = None

    id = get_song(ctx, song, cwd)
    if id not in (SENTINELS.NOT_IN_LIB, SENTINELS.MISSING_CWD):
        # open single song by path / alias
        info_to_set = (ctx.database.get_song_info(id),)
        paths_to_load = [info_to_set[0][0]['path']]
    else:
        # try as playlist name
        info, playlist_id = get_playlist_songs(ctx, song, return_id=True)
        if info is SENTINELS.PLAYLIST_EMPTY:
            playlist_id = None
            response = gen_response.Failed(f'can not open playlist \"{song}\" because it is empty')

        elif info is not SENTINELS.PLAYLIST_NOT_FOUND:
            # open playlist
            info_to_set = (info,)
            paths_to_load = list(map(lambda i: i['path'], info))

        else:
            # Not in library, try to open as path
            playlist_id = None
            path = None
            if Path(song).is_absolute():
                path = Path(song)
            else:
                if cwd is None:
                    response = gen_response.MissingCWD('open')
                else:
                    path = Path(cwd) / song

            if path is not None:
                if path.is_file():
                    info_to_set = ([{'path': str(path)}], False)
                    paths_to_load = [str(path)]
                else:
                    logger.warning(f'Can not open {path}')
                    response = gen_response.Failed(f'\"{song}\" can not parsed as an alias, library id, file path or playlist name')

    if paths_to_load is not None:
        if ctx.playback.current_song_info is None:
            current_paths = []
        else:
            current_paths = list(map(lambda s: s['path'], ctx.playback.current_song_info))

        if len(paths_to_load) == 1 and paths_to_load[0] in current_paths:
            num = current_paths.index(paths_to_load[0])
            response = gen_response.Success('song in current playlist. try to switch')
            response.append(_switch_song(ctx, num), joiner='->')
        else:
            ctx.playback.set_current_song(*info_to_set)
            response = _load_paths(ctx, paths_to_load, song)

            if response.ok():
                ctx.database.set_setting('last_is_all', '0')
                ctx.database.set_setting('last_song', song)
                ctx.database.set_setting('last_cwd', cwd)

                ctx.playback.current_playlist = playlist_id
                if playlist_id is not None:
                    last_num = ctx.database.get_playlist_last_num(playlist_id)
                    if last_num not in (None, SENTINELS.PLAYLIST_NOT_FOUND):
                        response += gen_response.Success('last played number detected, switching')
                        response.append(_switch_song(ctx, last_num), joiner='->')
                    else:
                        ctx.playback.set_current_num(0)

    return response

def _play_all_songs(ctx):
    info = ctx.database.get_all_song_info()
    if len(info) > 0:
        info = sort_songs(info)
        ctx.playback.set_current_song(info, True)
        paths = list(map(lambda x: x['path'], info))
        response = _load_paths(ctx, paths, 'all-songs')
        if response.ok():
            ctx.database.set_setting('last_is_all', '1')
            ctx.playback.current_playlist = SENTINELS.PLAY_ALL
            last_num = ctx.database.get_setting('last_play_all_num')
            if last_num not in (SENTINELS.SETTING_NOT_FOUND, None):
                last_num = int(last_num)

                response += gen_response.Success('last played number detected, switching')
                response.append(_switch_song(ctx, last_num), joiner='->')
            else:
                ctx.playback.set_current_num(0)
    else:
        response = gen_response.Failed('can not open all songs because there is none in library')
    return response

def _switch_song(ctx, num) -> gen_response.Response:
    max_num = len(ctx.player.medias)
    if num >= max_num:
        num_to_load = max_num - 1 # 9999999999 will switch the last song
    elif num < 0:
        num_to_load = max(max_num + num, 0) # -3 will switch the third from last song, -9999999999 will switch to the first song
    else:
        num_to_load = num
    result = ctx.player.load_number(num_to_load)

    if result is SENTINELS.SUCCESS:
        ctx.playback.set_current_num(ctx.player.number)

    response = {
        SENTINELS.SUCCESS: gen_response.Success(f'switched to the {num+1}nd song in current playlist: {ctx.playback.get_current_display_name()}'),
        SENTINELS.PLAYER_EMPTY: gen_response.PlayerEmpty(f'switch to the {num+1}nd song in current playlist'),
        SENTINELS.VLC_ERROR: gen_response.VLCError(f'switch to the {num+1}nd song in current playlist'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout(f'switch to the {num+1}nd song in current playlist'),
    }[result]
    if result is SENTINELS.SUCCESS:
        response += _jump_to_memorized_pos(ctx)

    return response

def _del_current_pos(ctx):
    if ctx.playback.current_song_info is not None:
        path = ctx.playback.get_playing_info()['path']
        ctx.database.del_pos(path)
    else:
        logger.warning('backend:del_current_pos is triggered before any song is loaded')

def _jump_to_memorized_pos(ctx) -> gen_response.Response:
    path = ctx.playback.get_playing_info()['path']
    pos = ctx.database.get_pos(path)
    if pos is not SENTINELS.POS_NOT_FOUND:
        response = gen_response.Success('try to jump to memorized pos')
        response.append(_jump_to_pos(ctx, pos), joiner='->')
        return response
    else:
        return gen_response.Success(f'no memorized position')

def _jump_to_pos(ctx, pos) -> gen_response.Response:
    result = ctx.player.jump_pos(pos)
    return {
        SENTINELS.SUCCESS: gen_response.Success(f'jumped to {format_time(pos)}'),
        SENTINELS.POS_TOO_LATE: gen_response.Failed(f'can not jumps to {format_time(pos)} because it is later than the end of the current song'), 
        SENTINELS.INVALID_PLAYER_STATE: gen_response.NotPlayingPaused('jump to progress')
    }[result]

def _replay(ctx) -> gen_response.Response:
    result = ctx.player.jump_pos(0)
    return {
        SENTINELS.SUCCESS: gen_response.Success('jumped to beginning'),
        SENTINELS.POS_TOO_LATE: gen_response.PosTooLate('jump to beginning'), # is this even possible?
        SENTINELS.INVALID_PLAYER_STATE: gen_response.NotPlayingPaused('jump to beginning')
    }[result]

def _load_paths(ctx, paths, song, jump_to_mem=True) -> gen_response.Response:
    result = ctx.player.load_paths(paths)
    response = {
        SENTINELS.SUCCESS: gen_response.Success(f'opened song/playlist \"{song}\"'),
        SENTINELS.PLAYER_LOAD_EMPTY: gen_response.Failed('can not load empty list of songs'),
        SENTINELS.VLC_ERROR: gen_response.VLCError('load path(s)'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('load path(s)'),
    }[result]
    if jump_to_mem and result is SENTINELS.SUCCESS:
        response += _jump_to_memorized_pos(ctx)
    return response

def _stop_player(ctx) -> gen_response.Response:
    result = ctx.player.stop()
    return {
        SENTINELS.SUCCESS: gen_response.Success('player stopped'),
        SENTINELS.VLC_ERROR: gen_response.VLCError('stop player'),
        SENTINELS.PLAYER_TIMEOUT: gen_response.PlayerTimeout('stop player')
    }[result]

def _switch_shuffle(ctx, direction): # direction: 1 / -1
    if len(ctx.playback.shuffle_order) > 0:
        shuffle_num = ctx.playback.shuffle_order.index(ctx.playback.current_song_num)
        shuffle_num += direction
        if shuffle_num >= len(ctx.playback.shuffle_order):
            shuffle_num = 0
            random.shuffle(ctx.playback.shuffle_order)
        elif shuffle_num < 0:
            shuffle_num = len(ctx.playback.shuffle_order) - 1
        return ctx.playback.shuffle_order[shuffle_num]
    else:
        return SENTINELS.PLAYER_EMPTY

def remove_from_current(ctx, path) -> gen_response.Response:
    if ctx.playback.current_song_info is not None:
        paths = list(map(lambda s: s['path'], ctx.playback.current_song_info))
        if path in paths:
            removed_num = paths.index(path)
            paths.remove(path)
            ctx.playback.current_song_info = ctx.playback.current_song_info[:removed_num] + ctx.playback.current_song_info[removed_num+1:]
            if len(paths) > 0:
                num = ctx.playback.current_song_num
                if removed_num < num: # removed before current
                    num -= 1
                elif removed_num == num:
                    if num >= len(paths):
                        num = len(paths) - 1

                response = _load_paths(ctx, paths, 'reload current playlist due to deleted song', jump_to_mem=False)
                response += _switch_song(ctx, num)
                return response
            else:
                ctx.playback.current_song_info = None
                ctx.playback.current_song_num = None
                ctx.playback.current_song_in_lib = False
                ctx.playback.current_playlist = None
                return _stop_player(ctx)
        else:
            return gen_response.Success('path not in current playlist') # not that anyone will actually read this but, you know, for good measure
    else:
        return gen_response.Success('current playlist empty') # same as above
