from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import syncedlyrics

from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.constants import ENCODING, LYRIC_FETCH_MAX_WORKERS
from src.sentinels import SENTINELS
from src import gen_response
from src.utils.misc import get_song_display_name
from src.utils.lyric import parse_lyric
from .helpers import get_song

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def set_(ctx, request):
    song = request['song']
    path = request['path']
    cwd = request.get('cwd', None)
    
    song_id = get_song(ctx, song, cwd)
    if song_id is SENTINELS.MISSING_CWD:
        return gen_response.MissingCWD('lib.lyric.set')
    elif song_id is SENTINELS.NOT_IN_LIB:
        return gen_response.SongNotExist(f'set lyric file of \"{song}\"')
    else:
        if path == '':
            path = SENTINELS.CLEAR_META
        ctx.database.set_song_meta(song_id, 'lyric', path)
        return gen_response.Success(f'set lyric file of \"{song}\"')

def show(ctx, request):
    song = request['song']
    cwd = request.get('cwd', None)

    song_id = get_song(ctx, song, cwd)
    if song_id is SENTINELS.MISSING_CWD:
        return gen_response.MissingCWD('lib.lyric.show')
    elif song_id is SENTINELS.NOT_IN_LIB:
        return gen_response.SongNotExist(f'show lyric of \"{song}\"')
    else:
        song_info = ctx.database.get_song_info(song_id)[0]
        lyric_path = song_info.get('lyric', None)
    
        if lyric_path is None:
            return gen_response.LyricNotExist()
        else:
            lyric = parse_lyric(lyric_path)
            if lyric is SENTINELS.FILE_IO_FAILED:
                return gen_response.FileIOFailed('open lyric file', lyric_path)
            else:
                attachment = {'path': lyric_path, 'lyric': lyric}
                return gen_response.Success('lyric obtained', attachment=attachment)

def fetch(ctx, request):
    songs = request['songs']
    cwd = request.get('cwd', None)

    failed = []
    paths = {}
    names = {}
    search_terms = []

    if len(songs) == 0:
        return gen_response.EmptyList('songs')
    else:
        for song in songs:
            song_id = get_song(ctx, song, cwd)
            if song_id is SENTINELS.MISSING_CWD:
                failed.append(gen_response.MissingCWD('lib.lyric.fetch'))
            elif song_id is SENTINELS.NOT_IN_LIB:
                failed.append(gen_response.SongNotExist(f'fetch lyric of {song}'))
            else:
                names[song_id] = song
                info = ctx.database.get_song_info(song_id)[0]

                path = str(Path(info['path']).with_suffix('.lrc'))
                paths[song_id] = path

                name = get_song_display_name(info)
                artist = info.get('artist', None)
                if artist is None:
                    artist = ''

                search_terms.append((song_id, f'{name} {artist}'.strip()))

        with ThreadPoolExecutor(max_workers=LYRIC_FETCH_MAX_WORKERS) as pool:
            results = list(pool.map(_fetch_lyric, search_terms))

        for song_id, lrc in results:
            if lrc is None:
                failed.append(gen_response.Failed(f'can not find lyric of {names[song_id]}'))
            else:
                path = paths[song_id]
                try:
                    with open(path, 'w', encoding=ENCODING) as f:
                        f.write(lrc)
                except OSError as e:
                    failed.append(gen_response.FileIOFailed('write lyric file', path, e))
                else:
                    ctx.database.set_song_meta(song_id, 'lyric', path)

        return gen_response.BatchAuto('Lyric fetched', len(failed), len(songs), failed=failed)

def _fetch_lyric(song):
    song_id, search_term = song
    lrc = syncedlyrics.search(
        search_term,
        synced_only=True,
    )
    return song_id, lrc