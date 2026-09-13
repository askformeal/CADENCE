from src import gen_response
from .playback.helpers import get_status, get_current_songs, get_current_lyric
from .library.helpers import get_song_playlist_names

def poll(ctx, request):
    snapshot = get_status(ctx)
    song_id = snapshot.get('id', None)
    if song_id is not None:
        snapshot['aliases'] = ctx.database.get_song_aliases(song_id)
        snapshot['added_playlists'] = get_song_playlist_names(ctx, song_id)
    else:
        snapshot['aliases'] = None
        snapshot['added_playlists'] = None
    lyric = get_current_lyric(ctx)
    snapshot['lyric'] = lyric.get('lyric', None)
    snapshot['lyric_loading'] = lyric.get('loading', False)
    snapshot['lyric_offset'] = lyric.get('offset', 0)
    snapshot['offset_overlay'] = lyric['offset_overlay']
    snapshot['current_songs'] = get_current_songs(ctx)
    playlists = ctx.database.get_all_playlists()
    snapshot['playlists'] = list(map(lambda x: x['name'], playlists))

    return gen_response.Success('snapshot obtained', attachment=snapshot)