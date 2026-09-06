from src.log import setup_logger

from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from .library import get_song

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def list_(ctx, request):
    song = request['song']
    cwd = request.get('cwd', None)
    
    id = get_song(ctx, song, cwd)
    if id is SENTINELS.MISSING_CWD:
        return gen_response.MissingCWD('lib.alias.list')
    elif id is not SENTINELS.NOT_IN_LIB:
        aliases = ctx.database.get_song_aliases(id)
        return gen_response.Success('obtained all aliases in library', aliases)
    else:
        return gen_response.SongNotExist(f'show aliases of {song}')

def bind(ctx, request):
    song = request['song']
    aliases = request['aliases']
    cwd = request.get('cwd', None)
    if len(aliases) == 0:
        return gen_response.EmptyList('aliases')
    else:
        id = get_song(ctx, song, cwd)
    
        if id is SENTINELS.MISSING_CWD:
            return gen_response.MissingCWD('lib.alias.bind')
        elif id is SENTINELS.NOT_IN_LIB:
            return gen_response.SongNotExist(f'bind alias to {song}')
        else:
            failed = []
            for alias in aliases:
                result = ctx.database.bind_alias(id, alias)
                bind_response = {
                    SENTINELS.SUCCESS: gen_response.Success(f"bound alias \"{alias}\" to song \"{song}\""),
                    SENTINELS.ALIAS_EXISTS: gen_response.Failed(f'can not bind alias \"{alias}\" because it is already bound to another song in library'),
                    SENTINELS.SONG_NOT_FOUND: gen_response.SongNotExist(f'bind alias to \"{song}\"') # not really necessary, but Monica insists
                }[result]
                if not bind_response.ok():
                    failed.append(bind_response)
    
            return gen_response.BatchAuto('aliases bound to song', len(failed), len(aliases), failed=failed)

def unbind(ctx, request):
    aliases = request['aliases']
    
    if len(aliases) == 0:
        return gen_response.EmptyList('aliases')
    else:
        failed = []
    
        for alias in aliases:
            result = ctx.database.unbind_alias(alias)
            if result is SENTINELS.ALIAS_NOT_FOUND:
                failed.append(gen_response.Failed(f'can not unbind {alias} because it does not exist in library'))
    
        return gen_response.BatchAuto('aliases unbound', len(failed), len(aliases), failed=failed)