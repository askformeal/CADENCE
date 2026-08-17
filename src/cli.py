import argparse
import sys
from pathlib import Path
import readchar
from time import sleep

from src import version
from src.sentinels import SENTINELS
from src.client import send_request, test_alive
from src.starter import start
from src.constants import RESTART_NUM, RESTART_POLL_INTERVAL, ATTACHMENT_REQUIRED_ACTIONS
from src.utils import format_ms

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

def main():
    is_reboot = False

    parser = argparse.ArgumentParser(prog=f'CADENCE {version}', epilog='CADENCE stands for Command-line Audio Decoding Engine with Navigation and Continuous Execution')

    command_sub = parser.add_subparsers(dest='action', required=True)

    start_parser = command_sub.add_parser('start', help='Start CADENCE backend')
    reboot_parser = command_sub.add_parser('reboot', help='Reboot CADENCE backend. Will fail if backend is not running')
    status_parser = command_sub.add_parser('status', help='Show CADENCE status')
    open_parser = command_sub.add_parser('open', help='Open a song or playlist. Supports alias, file path and playlist name')
    open_parser.add_argument('song', type=str, help='Song to open')
    play_all_parser = command_sub.add_parser('play-all', help='Play all songs in library')
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

    jump_parser = command_sub.add_parser('jump', help='Jump to progress of the current song')
    jump_parser.add_argument('progress', type=_percent, help='Progress to jump to (percentage)')
    restart_parser = command_sub.add_parser('restart', help='Clear memorized progress and jump to the beginning of the current playing song')

    volume_parser = command_sub.add_parser('volume', help='Set volume')
    volume_parser.add_argument('volume', type=_percent, help='Volume to set (percentage)')

    mute_parser = command_sub.add_parser('mute', help='Toggle mute')

    lib_parser = command_sub.add_parser('lib', help='Manage library')

    lib_sub = lib_parser.add_subparsers(dest='lib_action', required=True)

    lib_list_parser = lib_sub.add_parser('list', help='Show all songs in library')
    lib_list_parser.add_argument('-a', '--show-aliases', action='store_true', help='Show aliases of songs')

    lib_add_parser = lib_sub.add_parser('add', help='Add a new song to library')
    lib_add_parser.add_argument('path', type=_path, help='Path of the song to add')
    lib_add_parser.add_argument('-a', '--alias', type=str, default=None, help='Alias to bind to the new song')
    lib_add_parser.add_argument('--skip-meta', action='store_true', help='Disable automatic setting metadata')
    lib_add_parser.add_argument('--skip-alias', action='store_true', help='Disable automatic binding alias')

    lib_del_parser = lib_sub.add_parser('del', help='Delete a song from library')
    lib_del_parser.add_argument('song', type=str, help='Song to delete')

    lib_scan_parser = lib_sub.add_parser('scan', help='Scan a directory for all supported audio files and add them to library')
    lib_scan_parser.add_argument('dir', type=_path, help='directory to scan')
    lib_scan_parser.add_argument('--playlist', type=str, default=None, help='Playlist to add all found songs to')
    lib_scan_parser.add_argument('-r', '--recurse', action='store_true', help='Enable recursive scanning')
    lib_scan_parser.add_argument('-p', '--preview', action='store_true', help='Show found files without adding to library')
    lib_scan_parser.add_argument('--skip-meta', action='store_true', help='Disable automatic setting metadata')
    lib_scan_parser.add_argument('--skip-alias', action='store_true', help='Disable automatic binding alias')

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

    alias_parser = lib_sub.add_parser('alias', help='Manage aliases of songs in library')
    alias_sub = alias_parser.add_subparsers(dest='alias_action', required=True)
    alias_list_parser = alias_sub.add_parser('list', help='Show all bound aliases of a song in library')
    alias_list_parser.add_argument('song', type=str, help='Song to list aliases')

    alias_bind_parser = alias_sub.add_parser('bind', help='Bind an alias to a song in library')
    alias_bind_parser.add_argument('song', type=str, help='Song to bind aliases to')
    alias_bind_parser.add_argument('alias', type=str, help='alias to bind to song')

    alias_del_parser = alias_sub.add_parser('unbind', help='Unbind an alias from a song in library')
    alias_del_parser.add_argument('alias', type=str, help='Alias to delete')

    playlist_parser = lib_sub.add_parser('playlist', help='Manage playlists')
    playlist_sub = playlist_parser.add_subparsers(dest='playlist_action', required=True)

    playlist_list_parser = playlist_sub.add_parser('list', help='Show all songs in a playlist. Show names of all playlists in library if no playlists are given')
    playlist_list_parser.add_argument('playlist', type=str, nargs='?', default=None, help='Name of playlist to list')
    
    playlist_create_parser = playlist_sub.add_parser('create', help='Create a new playlist')
    playlist_create_parser.add_argument('name', type=str, help='Name of playlist to create')

    playlist_add_parser = playlist_sub.add_parser('add', help='Add a song in library to a playlist')
    playlist_add_parser.add_argument('song', help='Song to add to playlist')
    playlist_add_parser.add_argument('playlist', help='Playlist to add song to')

    playlist_kick_parser = playlist_sub.add_parser('kick', help='Remove a song from a playlist')
    playlist_kick_parser.add_argument('song', help='Song to remove from playlist')
    playlist_kick_parser.add_argument('playlist', help='Playlist to remove song from')

    playlist_del_parser = playlist_sub.add_parser('del', help='Delete a playlist')
    playlist_del_parser.add_argument('playlist', help='Playlist to delete')

    exit_parser = command_sub.add_parser('exit')

    args = vars(parser.parse_args())


    if args['action'] == 'start':
        _start_backend()

    else:
        if args.get('meta_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['meta_action']}"
            del args['meta_action']

        if args.get('alias_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['alias_action']}"
            del args['alias_action']

        if args.get('playlist_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['playlist_action']}"
            del args['playlist_action']

        if args.get('lib_action', None) is not None:
            args['action'] = f"{args['action']}.{args['lib_action']}"
            del args['lib_action']

        if  args['action'] == 'reboot':
            args['action'] = 'exit'
            is_reboot = True
        args['source'] = 'cli'
        args['cwd'] = str(Path.cwd())
        

        if args['action'] == 'lib.reset':
            answer = ''
            while not args['yes'] and answer not in ('y', 'n'):
                print('This action will reset the database and all data including songs and playlists will be permanently lost. Continue? [Y/N]', end='', flush=True)
                answer = readchar.readkey().lower()
                print()
            if answer == 'n':
                print('Cancelled')
                return
            del args['yes']

        response = send_request(**args)

        action = args['action']
        code =  response.get('code', None)
        msg = response.get('msg', None)
        attachment = response.get('attachment', None)
        failed = response.get('failed', [])

        if code is None or msg is None:
            print('[Failed]: Invalid response received from CADENCE backend')

        elif code == 0:
            print(f'[Succeeded]: {response['msg']}')

            if action == 'exit' and is_reboot:
                print('Waiting for backend to fully exit...')
                for i in range(RESTART_NUM):
                    sleep(RESTART_POLL_INTERVAL)
                    if not test_alive():
                        break
                else:
                    print('Timeout wait for backend to fully exit. Rebooting aborted')
                    return 1
                    
                print('Starting backend...')
                _start_backend()

            if action == 'lib.scan' and not args['preview']: # just to be clear
                if len(failed) > 0:
                    print('-'*50)
                    print('Failed to add the following file(s) to library:')
                    for add_response in failed:
                        print(f'  {add_response['msg']}')

            elif action in ATTACHMENT_REQUIRED_ACTIONS:
                if attachment is not None:
                    # these actions will be expecting an attachment
                    if action == 'status':
                        status = attachment
                        time = format_ms(status['time'])
                        length = format_ms(status['length'])
                        mute = {True: 'Yes', False: 'No'}[status['mute']]

                        print('\n'.join((f'Current path: {status['path']}',
                                         f'In library: {status['in_library']}',
                                         f'Player status: {status['player_status']}',
                                         f'Played time: {time}',
                                         f'Total length: {length}',
                                         f'Volume: {status['volume']}%',
                                         f'Mute: {mute}'
                                         )))

                    elif action == 'list':
                        info = attachment
                        _show_song_info(info, 'No songs are being played', show_num=True)

                    elif action == 'lib.list':
                        info = attachment
                        _show_song_info(info, 'No songs in library', show_aliases=args['show_aliases'])

                    elif action == 'lib.scan' and args['preview']:
                        if len(attachment) > 0:
                            print('-'*50)
                            for path in attachment:
                                print(path)
                        else:
                            print('No files to be shown')

                    elif action == 'lib.alias.list':
                        aliases = attachment
                        if len(aliases) > 0:
                            print('Alias(es):')
                            print(f'  {"\n  ".join(aliases)}')
                        else:
                            print('No aliases are bound to this song')

                    elif action == 'lib.playlist.list':
                        results = attachment
                        if args['playlist'] is not None:
                            _show_song_info(results, 'Playlist empty')
                        else:
                            if len(results) > 0:
                                print(f'Found {len(results)} playlist(s) in library:')
                                for playlist in results:
                                    print(f'  {playlist['name']}')
                            else:
                                print('No playlists in library')
                else:
                    print(f'[Failed]: action {action} was expecting an attachment but none was received from CADENCE backend')

        elif code == 1:
            print(f'[Failed]: {response['msg']}')
            if is_reboot:
                print('Failed to exit backend, rebooting aborted')

        elif code == 2:
            print('Failed to connect to CADENCE backend. You can try to use the start subcommand to start it')

        elif code == 3:
            print('[Failed]: received an unexpected default response code from CADENCE backend which is not to be used under any circumstances. Please report this BUG')

        elif code == 4:
            print('[Failed]: CADENCE backend is exiting')

        print()
        return code

def _start_backend():
    result = start()
    if result is SENTINELS.BACKEND_STARTED:
        print(f'CADENCE backend is now up and running')
    elif result is SENTINELS.BACKEND_ALREADY_RUNNING:
        print(f'CADENCE backend is already running')
    elif result is SENTINELS.FAILED_START_BACKEND:
        print(f'Failed to start CADENCE backend')
    return result

def _show_song_info(info, empty_msg, show_aliases=False, show_num=False):
    if len(info) > 0:
        for i in range(len(info)):
            song = info[i]
            texts = [
                f'Name: {song["name"]}',
                f'Path: {song["path"]}',
                f'Artist: {song["artist"]}',
                f'Album: {song["album"]}',
            ]
            if show_aliases:
                aliases = song['aliases']
                if len(aliases) > 0:
                    texts.append(f"Aliases: {', '.join(aliases)}")
                else:
                    texts.append('No aliases are bound to this song')
            max_len = max(map(len, texts))
            print('-'*(max_len))
            if show_num:
                print(f'{i+1}.')
            print('\n'.join(texts))
            print('-'*(max_len))
            print()
    else:
        print(empty_msg)

if __name__ == '__main__':
    sys.exit(main())
    