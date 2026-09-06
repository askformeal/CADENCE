from src.log import setup_logger

from src.constants import METADATA
from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from src.utils import extract_file_meta
from .library import get_song

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def set_(ctx, request):
    cwd = request.get('cwd', None)
    song_id = get_song(ctx, request['song'], cwd)
    if song_id is SENTINELS.MISSING_CWD:
        return gen_response.MissingCWD('lib.meta.set')
    elif song_id is SENTINELS.NOT_IN_LIB:
        return gen_response.SongNotExist(f"set metadata of \"{request['song']}\"")
    else:
        metadata = {}
        for label in METADATA:
            metadata[label] = request[label]

        if True in map(lambda x: x is not None, metadata.values()): # not all meta is none
            for label, value in metadata.items():
                if value is not None:
                    if value == '':
                        value = SENTINELS.CLEAR_META
                    ctx.database.set_song_meta(song_id, label, value)

            return gen_response.Success('metadata set')

        else:
            return gen_response.Failed(f'can not set metadata because no metadata was provided')

def read_file(ctx, request):
    song = request['song']
    cwd = request.get('cwd', None)

    song_id = get_song(ctx, song, cwd)
    set_all = request['all']
    if song_id is SENTINELS.MISSING_CWD:
        return gen_response.MissingCWD('lib.meta.read-file')
    elif song_id is SENTINELS.NOT_IN_LIB:
        return gen_response.SongNotExist(f"set metadata of \"{song}\"")
    else:
        count = 0
        path = ctx.database.get_song_info(song_id)[0]['path']
        file_meta = extract_file_meta(path)
        for label, value in file_meta.items():
            if value not in ('', None) and (request[label] or set_all):
                ctx.database.set_song_meta(song_id, label, value)
                count += 1
        return gen_response.Success(f'{count} metadata set')