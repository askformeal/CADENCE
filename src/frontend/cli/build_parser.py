import argparse
from pathlib import Path

from src import __version__
from src.constants import REPO_LINK

def _path(val):
    return str(Path(val).absolute())

def _percent(val):
    try:
        val = int(val)
    except ValueError:
        raise argparse.ArgumentTypeError(f'{val} is not a valid percentage number')
    else:
        if val < 0 or val > 100:
            raise argparse.ArgumentTypeError(f'percentage must not be lower than 0 or higher than 100')
        else:
            return val

def build_parser():
    parser = argparse.ArgumentParser(prog=f'CADENCE {__version__}', epilog=f'GitHub Repository: {REPO_LINK}')

    command_sub = parser.add_subparsers(dest='action', required=True)

    start_parser = command_sub.add_parser('start', help='Start CADENCE backend')
    start_parser.add_argument('-c', '--continue', action='store_true', help='Continue playing last song')
    start_parser.add_argument('--dev', action='store_true', help='Start in development mode')

    reboot_parser = command_sub.add_parser('reboot', help='Reboot CADENCE backend. Will fail if backend is not running')
    reboot_parser.add_argument('--dev', action='store_true', help='Reboot in development mode')
    reboot_parser.add_argument('-c', '--continue', action='store_true', help='Continue playing last song')

    dash_parser = command_sub.add_parser('dash', help='Open Dashboard')

    status_parser = command_sub.add_parser('status', help='Show CADENCE status')

    open_parser = command_sub.add_parser('open', help='Open a song or playlist. Supports alias, file path and playlist name')
    open_parser.add_argument('song', type=str, help='Song to open')

    play_all_parser = command_sub.add_parser('play-all', help='Play all songs in library')

    reload_parser = command_sub.add_parser('reload', help='Reload current songs')

    pause_parser = command_sub.add_parser('pause', help='Pause playing media')

    resume_parser = command_sub.add_parser('resume', help='Resume paused media')

    toggle_parser = command_sub.add_parser('toggle', help='Switch between playing and paused')

    stop_parser = command_sub.add_parser('stop', help='Stop playing')

    list_parser = command_sub.add_parser('list', help='Show current playlist')

    loop_parser = command_sub.add_parser('loop', help='Toggle loop mode')

    shuffle_parser = command_sub.add_parser('shuffle', help='Toggle shuffle mode')

    dice_parser = command_sub.add_parser('dice', help='Switch to a random song in current playlist')

    switch_parser = command_sub.add_parser('switch', help='Switch to a song in current playlist via number')
    switch_parser.add_argument('number', type=int, help='Number in playlist of song to switch. Negative number means count from the last')

    prev_parser = command_sub.add_parser('prev', help='Switch to the previous song in current playlist')

    next_parser = command_sub.add_parser('next', help='Switch to the next song in current playlist')

    seek_parser = command_sub.add_parser('seek', help='Jump to a specific time')
    seek_parser.add_argument('time', help='Time to jump to (HH:MM:SS)')

    jump_parser = command_sub.add_parser('jump', help='Jump to progress of the current song')
    jump_parser.add_argument('progress', type=_percent, help='Progress to jump to (percentage)')

    replay_parser = command_sub.add_parser('replay', help='Clear memorized progress and jump to the beginning of the current playing song')

    volume_parser = command_sub.add_parser('volume', help='Set volume')
    volume_parser.add_argument('volume', type=str, help='Volume to set (percentage)')

    mute_parser = command_sub.add_parser('mute', help='Toggle mute')

    lyric_parser = command_sub.add_parser('lyric', help='Switch between lyric sources [local/online]')

    lib_parser = command_sub.add_parser('lib', help='Manage library')

    lib_sub = lib_parser.add_subparsers(dest='lib_action', required=True)

    lib_info_parser = lib_sub.add_parser('info', help='Show information of a song')
    lib_info_parser.add_argument('songs', type=str, nargs='+', help='Song to show')
    lib_info_parser.add_argument('-a', '--show-aliases', action='store_true', help='Show aliases of the song')
    lib_info_parser.add_argument('-p', '--show-playlists', action='store_true', help='Show playlists the song is in')

    lib_list_parser = lib_sub.add_parser('list', help='Show all songs in library')
    lib_list_parser.add_argument('-a', '--show-aliases', action='store_true', help='Show aliases of songs')
    lib_list_parser.add_argument('-p', '--show-playlists', action='store_true', help='Show playlists each song is in')
    lib_list_parser.add_argument('-t', '--show-tech', action='store_true', help='Show technical information')

    lib_search_parser = lib_sub.add_parser('search', help='Search for songs in library')
    lib_search_parser.add_argument('keyword', type=str, nargs='+', help='Keyword to search')
    lib_search_parser.add_argument('-o', '--or', action='store_true', help='Get all results that match any one the keywords')

    lib_add_parser = lib_sub.add_parser('add', help='Add songs to library')
    lib_add_parser.add_argument('paths', type=_path, nargs='+', help='Path of songs to add')
    lib_add_parser.add_argument('-a', '--aliases', type=str, nargs='+', default=[], help='Aliases to bind to the new songs')
    lib_add_parser.add_argument('--skip-meta', action='store_true', help='Disable automatic setting metadata')
    lib_add_parser.add_argument('--skip-alias', action='store_true', help='Disable automatic binding aliases')
    lib_add_parser.add_argument('--skip-lyric', action='store_true', help='Disable automatic setting lyric file')
    lib_add_parser.add_argument('--loose-path', action='store_true', help='Adding songs without checking the availability of the paths. May cause automatic setting of metadata and binding of aliases to fail')

    lib_del_parser = lib_sub.add_parser('del', help='Delete songs from library')
    lib_del_parser.add_argument('songs', type=str, nargs='+', help='Songs to delete')

    lib_prune_parser = lib_sub.add_parser('prune', help='Delete all songs which file no longer exists')
    lib_prune_parser.add_argument('-d', '--dry-run', action='store_true', help='Show found files without deleting')

    lib_scan_parser = lib_sub.add_parser('scan', help='Scan a directory for all supported audio files and add them to library')
    lib_scan_parser.add_argument('dir', type=_path, help='directory to scan')
    lib_scan_parser.add_argument('--playlist', type=str, default=None, help='Playlist to add all found songs to')
    lib_scan_parser.add_argument('-r', '--recurse', action='store_true', help='Enable recursive scanning')
    lib_scan_parser.add_argument('-d', '--dry-run', action='store_true', help='Show found files without adding to library')
    lib_scan_parser.add_argument('--skip-meta', action='store_true', help='Disable automatic setting metadata')
    lib_scan_parser.add_argument('--skip-alias', action='store_true', help='Disable automatic binding alias')
    lib_scan_parser.add_argument('--skip-lyric', action='store_true', help='Disable automatic setting lyric file')

    lib_reset_parser = lib_sub.add_parser('reset', help='Reset library and delete all data')
    lib_reset_parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation')

    meta_epilog = '\n'.join(('Supported metadata:',
                             '  name: The name of the song. Can not be used to reference the song like alias',
                             '  artist: The artist of the song',
                             '  album: The album of the song'))
    meta_parser = lib_sub.add_parser('meta', help='Manage metadata of songs in library', epilog=meta_epilog)
    meta_sub = meta_parser.add_subparsers(dest='meta_action', required=True)

    meta_set_parser = meta_sub.add_parser('set', help='Set the value of metadata of a song in library. Using empty string (\"\") to clear a metadata')
    meta_set_parser.add_argument('song', type=str, help='Song to set metadata')
    meta_set_parser.add_argument('--name', type=str, default=None, help='Name of the song')
    meta_set_parser.add_argument('--artist', type=str, default=None, help='Artist of the song')
    meta_set_parser.add_argument('--album', type=str, default=None, help='Album of the song')

    meta_read_file_parser = meta_sub.add_parser('read-file', help='Set the value of metadata of a song in library with values read from file')
    meta_read_file_parser.add_argument('song', type=str, help='Song to set metadata')
    meta_read_file_parser.add_argument('--name', action='store_true', help='Set name of the song')
    meta_read_file_parser.add_argument('--artist', action='store_true', help='Set artist of the song')
    meta_read_file_parser.add_argument('--album', action='store_true', help='Set album of the song')
    meta_read_file_parser.add_argument('--all', action='store_true', help='Set all available metadata')

    alias_parser = lib_sub.add_parser('alias', help='Manage aliases of songs in library')
    alias_sub = alias_parser.add_subparsers(dest='alias_action', required=True)

    alias_list_parser = alias_sub.add_parser('list', help='Show all bound aliases of a song in library')
    alias_list_parser.add_argument('song', type=str, help='Song to list aliases')

    alias_bind_parser = alias_sub.add_parser('bind', help='Bind aliases to a song in library')
    alias_bind_parser.add_argument('song', type=str, help='Song to bind aliases to')
    alias_bind_parser.add_argument('aliases', type=str, nargs='+', help='aliases to bind to song')

    alias_unbind_parser = alias_sub.add_parser('unbind', help='Unbind aliases from their songs in library')
    alias_unbind_parser.add_argument('aliases', type=str, nargs='+', help='Aliases to unbind')

    lyric_parser = lib_sub.add_parser('lyric', help='Manage lyrics')
    lyric_sub = lyric_parser.add_subparsers(dest='lyric_action', required=True)

    lyric_set_parser = lyric_sub.add_parser('set', help='Set lyric file of a song. Using empty string (\"\") to unset')
    lyric_set_parser.add_argument('song', type=str, help='Song to set lyric file')
    lyric_set_parser.add_argument('path', type=_path, help='Path of lyric file')

    lyric_show_parser = lyric_sub.add_parser('show', help='Show lyric of a song')
    lyric_show_parser.add_argument('song', type=str, help='Song to show lyric')

    lyric_fetch_parser = lyric_sub.add_parser('fetch', help='Fetch lyric of songs from online sources')
    lyric_fetch_parser.add_argument('songs', type=str, nargs='+', help='Songs to fetch lyric')

    lyric_offset_parser = lyric_sub.add_parser('offset', help='Set lyric offset of song')
    lyric_offset_parser.add_argument('song', type=str, help='Song to set offset')
    lyric_offset_parser.add_argument('offset', type=int, help='Offset to set (ms)')


    playlist_parser = lib_sub.add_parser('playlist', help='Manage playlists')
    playlist_sub = playlist_parser.add_subparsers(dest='playlist_action', required=True)

    playlist_list_parser = playlist_sub.add_parser('list', help='Show all songs in a playlist. Show names of all playlists in library if no playlists are provided')
    playlist_list_parser.add_argument('playlist', type=str, nargs='?', default=None, help='Name of playlist to list')
    playlist_list_parser.add_argument('-a', '--show-aliases', action='store_true', help='Show aliases of songs')
    playlist_list_parser.add_argument('-p', '--show-playlists', action='store_true', help='Show playlists each song is in')
    playlist_list_parser.add_argument('-t', '--show-tech', action='store_true', help='Show technical information')
    
    playlist_create_parser = playlist_sub.add_parser('create', help='Create a new playlist')
    playlist_create_parser.add_argument('name', type=str, help='Name of playlist to create')

    playlist_add_parser = playlist_sub.add_parser('add', help='Add songs in library to a playlist')
    playlist_add_parser.add_argument('playlist', type=str, help='Playlist to add song to')
    playlist_add_parser.add_argument('songs', type=str, nargs='+', help='Songs to add to playlist')

    playlist_kick_parser = playlist_sub.add_parser('kick', help='Remove songs from a playlist')
    playlist_kick_parser.add_argument('playlist', type=str, help='Playlist to remove song from')
    playlist_kick_parser.add_argument('songs', type=str, nargs='+', help='Songs to remove from playlist')

    playlist_del_parser = playlist_sub.add_parser('del', help='Delete a playlist')
    playlist_del_parser.add_argument('playlist', type=str, help='Playlist to delete')

    config_parser = command_sub.add_parser('config', help='Manage configuration')
    config_sub = config_parser.add_subparsers(dest='config_action', required=True)
    config_parent = argparse.ArgumentParser(add_help=False)
    config_parent.add_argument('-d', '--direct', action='store_true', help='Bypass CADENCE backend and operate on local configure file directly')

    config_list_parser = config_sub.add_parser('list', parents=[config_parent], help='Show information all options')

    config_show_parser = config_sub.add_parser('show', parents=[config_parent], help='Show information of an option')
    config_show_parser.add_argument('option', type=str, help='Option to show')

    config_set_parser = config_sub.add_parser('set', parents=[config_parent], help='Set value of an option. You might need to reboot CADENCE backend to make some options take effect')
    config_set_parser.add_argument('option', type=str, help='Option to set')
    config_set_parser.add_argument('value', type=str, help='Value to set')
    config_set_parser.add_argument('--overwrite-corrupt', action='store_true', help='Overwrite corrupted configure file.')

    config_unset_parser = config_sub.add_parser('unset', parents=[config_parent], help='Remove the setting of an option from configure file and fallback to default value')
    config_unset_parser.add_argument('option', type=str, help='Option to unset')

    config_open_parser = config_sub.add_parser('open', parents=[config_parent], help='Open configure file with system\'s default application')

    config_path_parser = config_sub.add_parser('path', parents=[config_parent], help='Show path of configure file')

    exit_parser = command_sub.add_parser('exit', help='Exit CADENCE backend')

    kill_parser = command_sub.add_parser('kill', help='Kill all CADENCE backend processes. May cause unpredictable error')

    return parser