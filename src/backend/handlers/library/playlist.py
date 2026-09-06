from src.log import setup_logger
from src.constants import BACKEND_LOG_PATH
from src.sentinels import SENTINELS
from src import gen_response
from .library import get_song, get_playlist_songs, insert_songs_aliases, insert_songs_playlist_names

logger = setup_logger(__name__, BACKEND_LOG_PATH)

def list_(ctx, request):    
    playlist = request['playlist']
    if playlist is not None:
        response = gen_response.Success(f'obtained song in playlist \"{playlist}\"')
        info = get_playlist_songs(ctx, playlist)

        if info is SENTINELS.PLAYLIST_NOT_FOUND:
            return gen_response.PlaylistNotExist(f'list songs of playlist \"{playlist}\"')
        elif info is SENTINELS.PLAYLIST_EMPTY:
            response.attachment = []
        else:
            if request['show_aliases']:
                info = insert_songs_aliases(ctx, info)
    
            if request['show_playlists']:
                info = insert_songs_playlist_names(ctx, info)
    
            response.attachment = info

        return response
    else:
        playlists = ctx.database.get_all_playlists()
        return gen_response.Success('obtained list of playlist in library', attachment=playlists)

def create(ctx, request):
    name = request['name']
    ignored = ctx.database.create_playlist(name)[1]
    if not ignored:
        return gen_response.Success(f'created playlist \"{name}\"')
    else:
        return gen_response.Failed(f'can not create \"{name}\" because a playlist of the same name already exists in library')

def add(ctx, request):
    playlist = request['playlist']
    songs = request['songs']
    cwd = request.get('cwd', None)
    
    if len(songs) == 0:
        return gen_response.EmptyList('songs')
    else:
        playlist_id = ctx.database.get_playlist_via_name(playlist)
    
        if playlist_id is SENTINELS.PLAYLIST_NOT_FOUND:
            return gen_response.PlaylistNotExist(f'add song to playlist \"{request['playlist']}\"')
        else:
            failed = []
            for song in songs:
                song_id = get_song(ctx, song, cwd)
                if song_id is SENTINELS.MISSING_CWD:
                    failed.append(gen_response.MissingKey('lib.playlist.add', 'cwd'))
                elif song_id is SENTINELS.NOT_IN_LIB:
                    failed.append(gen_response.SongNotExist(f'add song \"{song}\" to playlist \"{playlist}\"'))
                else:
                    ignored = ctx.database.add_song_to_playlist(playlist_id, song_id)
                    if ignored:
                        failed.append(gen_response.Failed(f'can not add song \"{song}\" to playlist \"{playlist}\" because it is already in the playlist'))
    
            return gen_response.BatchAuto('songs added to playlist', len(failed), len(songs), failed=failed)                                            

def kick(ctx, request):
    playlist = request['playlist']
    songs = request['songs']
    cwd = request.get('cwd', None)
    
    if len(songs) == 0:
        return gen_response.EmptyList('songs')
    else:                    
        playlist_id = ctx.database.get_playlist_via_name(playlist)
        if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
            failed = []
            for song in songs:
                song_id = get_song(ctx, song, cwd)
                if song_id is SENTINELS.MISSING_CWD:
                    failed.append(gen_response.MissingKey('lib.playlist.kick', 'cwd'))
                elif song_id is SENTINELS.NOT_IN_LIB:
                    failed.append(gen_response.SongNotExist(f'remove song \"{song}\" from playlist \"{playlist}\"'))
                else:
                    result = ctx.database.del_song_from_playlist(playlist_id, song_id)
                    if result is SENTINELS.PLAYLIST_SONG_NOT_FOUND:
                        failed.append(gen_response.Failed(f"can not remove song \"{song}\" from playlist \"{playlist}\" because the song is not in the playlist"))
    
            return gen_response.BatchAuto('songs removed from playlist', len(failed), len(songs), failed=failed)
        else:
            return gen_response.PlaylistNotExist(f"remove song(s) from playlist {playlist}")

def del_(ctx, request):
    playlist_id = ctx.database.get_playlist_via_name(request['playlist'])
    if playlist_id is not SENTINELS.PLAYLIST_NOT_FOUND:
        ctx.database.del_playlist(playlist_id)
        return gen_response.Success(f"deleted playlist \"{request['playlist']}\"")
    else:
        return gen_response.PlaylistNotExist(f"delete playlist \"{request['playlist']}\"")

