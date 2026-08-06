import argparse
import sys
from pathlib import Path
import readchar

from src import version
from src.sentinels import SENTINELS
from src.client import send_request
from src.starter import start

def _path(val):
    return str(Path(val).absolute())

def main():
    parser = argparse.ArgumentParser(prog=f'CADENCE {version}')

    command_sub = parser.add_subparsers(dest='action', required=True)

    start_parser = command_sub.add_parser('start', help='Start CADENCE backend')
    status_parser = command_sub.add_parser('status', help='Show CADENCE status')
    open_parser = command_sub.add_parser('open', help='Open a song or playlist. Supports alias, file path and playlist name')
    open_parser.add_argument('song', type=str, help='Song to open')
    pause_parser = command_sub.add_parser('pause', help='Pause playing media')
    resume_parser = command_sub.add_parser('resume', help='Resume paused media')
    toggle_parser = command_sub.add_parser('toggle', help='Switch between playing and paused')
    stop_parser = command_sub.add_parser('stop', help='Stop playing')
    prev_parser = command_sub.add_parser('prev', help='Switch to the previous song in current playlist')
    next_parser = command_sub.add_parser('next',help='Switch to the next song in current playlist')

    lib_parser = command_sub.add_parser('lib', help='Manage library')

    lib_sub = lib_parser.add_subparsers(dest='lib_action', required=True)

    lib_list_parser = lib_sub.add_parser('list', help='Show all songs in library')
    lib_list_parser.add_argument('-a', '--show-aliases', action='store_true', help='Show aliases of songs')

    lib_add_parser = lib_sub.add_parser('add', help='Add a new song to library')
    lib_add_parser.add_argument('path', type=_path, help='Path of the song to add')
    lib_del_parser = lib_sub.add_parser('del', help='Delete a song from library')
    lib_del_parser.add_argument('song', type=str, help='Song to delete')
    lib_reset_parser = lib_sub.add_parser('reset', help='Reset library and delete all data')

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

    playlist_list_parser = playlist_sub.add_parser('list', help='Show all playlists in library')
    
    playlist_create_parser = playlist_sub.add_parser('create', help='Create a new playlist')
    playlist_create_parser.add_argument('name', type=str, help='Name of playlist to create')

    playlist_add_parser = playlist_sub.add_parser('add', help='Add a song in library to a playlist')
    playlist_add_parser.add_argument('song', help='Song to add to playlist')
    playlist_add_parser.add_argument('playlist', help='Playlist to add song to')

    exit_parser = command_sub.add_parser('exit')

    args = vars(parser.parse_args())

    if args['action'] == 'start':
        result = start()
        if result is SENTINELS.BACKEND_STARTED:
            print(f'CADENCE backend is now up and running')
        elif result is SENTINELS.BACKEND_ALREADY_RUNNING:
            print(f'CADENCE backend is already running')
        elif result is SENTINELS.FAILED_START_BACKEND:
            print(f'Failed to start CADENCE backend')
   
    else:
        if args.get('alias_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['alias_action']}"
            del args['alias_action']

        if args.get('playlist_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['playlist_action']}"
            del args['playlist_action']

        if args.get('lib_action', None) is not None:
            args['action'] = f'{args["action"]}.{args['lib_action']}'
            del args['lib_action']

        args['source'] = 'teletypewriter interface (non-interactive)'
        args['cwd'] = str(Path.cwd())

        if args['action'] == 'lib.reset':
            answer = ''
            while answer not in ('y', 'n'):
                print('This action will reset the database and all data including songs and playlists will be permanently lost. Continue? [Y/N]', end='', flush=True)
                answer = readchar.readkey().lower()
                print()
            if answer == 'n':
                print('Cancelled')
                return

        response = send_request(**args)

        if response['code'] == 0:
            print('[Succeeded]')
            if args['action'] == 'status':
                status = response['attachment']
                time = status['time']
                length = status['length']
                if time == -1:
                    time = '--:--'
                elif time == 0:
                    time = '00:00'
                else:
                    time /= 1000
                    minutes = int(time / 60)
                    seconds = int(time % 60)
                    time = f'{minutes:02d}:{seconds:02d}'

                if length == -1:
                    length = '--:--'
                elif length == 0:
                    length = '00:00'
                else:
                    length /= 1000
                    minutes = int(length / 60)
                    seconds = int(length % 60)
                    length = f'{minutes:02d}:{seconds:02d}'

                print(f"Current path: {status['path']}\nIn library: {status['in_library']}\nPlayer status: {status['player_status']}\nPlayed time: {time}\nTotal length: {length}")

            elif args['action'] == 'lib.list':
                info = response['attachment']
                if len(info) > 0:
                    for song in info:
                        texts = [
                            f'Path: {song["path"]}'
                        ]
                        if args['show_aliases']:
                            texts.append(f"Aliases: {', '.join(song['aliases'])}")
                        max_len = max(map(len, texts))
                        print('-'*(max_len))
                        print(f'#{song["id"]}.')
                        print('\n'.join(texts))
                        print('-'*(max_len))
                        print()
                else:
                    print('Library Empty')

            elif args['action'] == 'lib.alias.list':
                aliases = response['attachment']
                if len(aliases) > 0:
                    print('Alias(es):')
                    print(f'  {"\n  ".join(aliases)}')
                else:
                    print('No aliases are bound to this song')

            elif args['action'] == 'lib.playlist.list':
                playlists = response['attachment']
                print(playlists) # will prettify output latter

        else:
            print(f'[Failed]: {response['msg']}')

        sys.exit(response['code'])

if __name__ == '__main__':
    main()