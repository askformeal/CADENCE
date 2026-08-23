import argparse
import sys
from pathlib import Path
import readchar
from time import sleep

from src import version
from src.sentinels import SENTINELS
from src.client import send_request, test_alive
from src.process import start, kill
from src.constants import RESTART_NUM, RESTART_POLL_INTERVAL, ATTACHMENT_REQUIRED_ACTIONS
from src.utils import format_time, box

class SongOutput:
    # generate outputs of from song info
    def __init__(self, info=None):
        if info is None:
            info = {}
        self.extract_from_dict(info)

    def extract_from_dict(self, info):      

        self.name = info.get('name', '?')

        self.artist = info.get('artist', '?')
        self.album = info.get('album', '?')

        self.duration = format_time(info.get('duration', -1))
        self.bitrate = info.get('bitrate', '?')
        if isinstance(self.bitrate, int):
            self.bitrate = f'{self.bitrate/1000:.10g}'
        self.sample_rate = info.get('sample_rate', '?')
        self.channels = info.get('channels', '?')

        self.path = info.get('path', '?')

        self.in_lib = {True: 'Yes', False: 'No', '?': '?'}[info.get('in_library', '?')]
        self.lib_id = info.get('id', '?')

        self.aliases = info.get('aliases', '?')
        self.aliases_num = '?'
        if self.aliases != '?':
            self.aliases_num = len(self.aliases)
            if len(self.aliases) > 0:
                self.aliases = ', '.join(self.aliases)
            else:
                self.aliases = 'No aliases are bond to this song'

        self.playlists = info.get('playlists', '?')
        self.playlists_num = '?'
        if self.playlists != '?':
            self.playlists_num = len(self.playlists)
            if len(self.playlists) > 0:
                self.playlists = ', '.join(self.playlists)
            else:
                self.playlists = '[This song is not in any playlists]'

        self.player_status = info.get('player_status', '?')

        raw_time = info.get('time', -1)
        raw_length = info.get('length', -1)

        self.time = format_time(raw_time)
        self.length = format_time(raw_length)
    
        if raw_length != -1:
            self.percentage = f'{raw_time / raw_length * 100:.0f}'
        else:
            self.percentage = '--'

        self.volume = info.get('volume', '?')
        self.mute = {True: 'Yes', False: 'No', '?': '?'}[info.get('mute', '?')]

        self.playlist_len = info.get('playlist_len', '?')

        self.current_num = info.get('current_num', '?')
        if isinstance(self.current_num, int):
            self.current_num += 1
    
        self.run_time = format_time(info.get('run_time', -1), 'sec')
    
        self.dev = info.get('dev', False)

        if self.name is None:
            if self.path != '?' and self.path is not None:
                self.display_name = Path(self.path).stem
            else:
                self.display_name = None
        else:
            self.display_name = self.name

        for key, value in vars(self).items():
            if value is None:
                setattr(self, key, 'N/A')

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
    start_parser.add_argument('-c', '--continue', action='store_true', help='Continue playing last song')
    start_parser.add_argument('--dev', action='store_true', help='Start in development mode')

    reboot_parser = command_sub.add_parser('reboot', help='Reboot CADENCE backend. Will fail if backend is not running')
    reboot_parser.add_argument('--dev', action='store_true', help='Reboot in development mode')
    reboot_parser.add_argument('-c', '--continue', action='store_true', help='Continue playing last song')

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

    seek_parser = command_sub.add_parser('seek', help='Jump to a specific time')
    seek_parser.add_argument('time', help='Time to jump to (HH:MM:SS)')

    jump_parser = command_sub.add_parser('jump', help='Jump to progress of the current song')
    jump_parser.add_argument('progress', type=_percent, help='Progress to jump to (percentage)')

    replay_parser = command_sub.add_parser('replay', help='Clear memorized progress and jump to the beginning of the current playing song')

    volume_parser = command_sub.add_parser('volume', help='Set volume')
    volume_parser.add_argument('volume', type=_percent, help='Volume to set (percentage)')

    mute_parser = command_sub.add_parser('mute', help='Toggle mute')

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

    config_show_parser = config_sub.add_parser('show', help='Show value of an option')
    config_show_parser.add_argument('option', type=str, help='Option to show')

    config_set_parser = config_sub.add_parser('set', help='Set value of an option. You might need to reboot CADENCE backend to make some options take effect')
    config_set_parser.add_argument('option', type=str, help='Option to set')
    config_set_parser.add_argument('value', type=str, help='Value to set')
    config_set_parser.add_argument('--overwrite-corrupt', action='store_true', help='Overwrite corrupted configure file.')

    config_unset_parser = config_sub.add_parser('unset', help='Remove the setting of an option from configure file and fallback to default value')
    config_unset_parser.add_argument('option', type=str, help='Option to unset')

    exit_parser = command_sub.add_parser('exit', help='Exit CADENCE backend')

    kill_parser = command_sub.add_parser('kill', help='Kill all CADENCE backend processes. May cause unpredictable error')

    args = vars(parser.parse_args())


    if args['action'] == 'start':
        notifies = _start_backend(CADENCE_DEV=int(args['dev']), CADENCE_CONTINUE=int(args['continue']))[1]
        _show_notifies(notifies)

    elif args['action'] == 'kill':
        print(f'Killing CADENCE backend processes...')
        result = kill()
        for pid, process_result in result:
            msg = {
                SENTINELS.PERMISSION_INSUFFICIENT: 'Access Denied',
                SENTINELS.INVALID_PID: 'PID Invalid',
                SENTINELS.PROCESS_NOT_FOUND: 'Process Not Exist',
                SENTINELS.GRACE_KILL: 'Gracefully Terminated',
                SENTINELS.FORCE_KILL: 'Forcefully Killed'
            }[process_result]

            print(f' PID {pid}: {msg}')

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

        if args.get('config_action', None) is not None:
            args['action'] = f"{args['action']}.{args['config_action']}"
            del args['config_action']

        if  args['action'] == 'reboot':
            args['action'] = 'exit'
            is_reboot = True      

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

# -------------------------------------- Pre-response --------------------------------------

        response = send_request(**_wrap_request(args))

# -------------------------------------- Post-response --------------------------------------

        action = args['action']
        code =  response.get('code', None)
        msg = response.get('msg', None)
        attachment = response.get('attachment', None)
        failed = response.get('failed', [])
        notifies = response.get('notifies', [])

        _show_notifies(notifies)

        if code is None or msg is None:
            print('[Failed]: Invalid response received from CADENCE backend')

        elif code == 0:
            print(box(f'[Succeeded]: {response['msg']}'))

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
                notifies = _start_backend(CADENCE_DEV=int(args['dev']), CADENCE_CONTINUE=int(args['continue']))[1]

                _show_notifies(notifies)

            elif action == 'lib.add' and isinstance(attachment, list):
                for add_response in attachment:
                    print(add_response['msg'])

            elif action in ATTACHMENT_REQUIRED_ACTIONS:
                if attachment is None and not (action == 'lib.scan' and not args['dry_run']):
                    print(f'[Failed]: action {action} was expecting an attachment but none was received from CADENCE backend')
                else:
                    # these actions will be expecting an attachment
                    if action == 'status':
                        
                        output = SongOutput(attachment)

                        text = '\n'.join((
                                        f'\n{output.name} - {output.artist} [{output.current_num} / {output.playlist_len}]',
                                        f'[{output.time} / {output.length}] {output.percentage}%\n',
                                        f'In library: {output.in_lib}',
                                        f'Album: {output.album}',
                                        f'Path: {output.path}\n',
                                        f'Player status: {output.player_status}',
                                        f'Volume: {output.volume}%',
                                        f'Mute: {output.mute}',
                                        f'\nCADENCE backend had been running for {output.run_time}',
                        ))

                        if output.dev:
                            text += '\n\nDEVELOPMENT MODE ON'

                        print(box(text))

                    elif action == 'list':
                        _show_song_info(attachment, 'No songs are being played', show_num=True)

                    elif action == 'lib.info':
                        _show_song_info(attachment, 
                                        show_tech=True, 
                                        show_aliases=args['show_aliases'],
                                        show_playlists=args['show_playlists'])

                    elif action == 'lib.list':
                        _show_song_info(attachment, 
                                        'No songs in library', 
                                        show_tech=args['show_tech'],
                                        show_aliases=args['show_aliases'], 
                                        show_playlists=args['show_playlists'])

                    elif action == 'lib.search':
                        _show_song_info(attachment, 'No results to be shown')

                    elif action == 'lib.prune':
                        _show_song_info(attachment, 'No songs to be shown')

                    elif action == 'lib.scan' and args['dry_run']:
                        if len(attachment) > 0:
                            print('-'*50)
                            for path in attachment:
                                print(path)
                        else:
                            print('No files to be shown')

                    elif action == 'lib.alias.list':
                        if len(attachment) > 0:
                            print('Alias(es):')
                            print(f'  {"\n  ".join(attachment)}')
                        else:
                            print('No aliases are bound to this song')

                    elif action == 'lib.playlist.list':
                        if args['playlist'] is not None:
                            _show_song_info(attachment, 
                                            'Playlist empty',
                                            show_tech=args['show_tech'],
                                            show_aliases=args['show_aliases'],
                                            show_playlists=args['show_playlists'])
                        else:
                            if len(attachment) > 0:
                                print(f'Found {len(attachment)} playlist(s) in library:')
                                for playlist in attachment:
                                    print(f'  {playlist['name']}')
                            else:
                                print('No playlists in library')

                    elif action == 'config.show':
                        value = attachment.get('value', 'N/A')
                        source = attachment.get('source', 'N/A')
                        print(box(f'{args['option']}: {value} | loaded from {source}'))

        elif code == 1:
            print(box(f'[Failed]: {response['msg']}'))
            if is_reboot:
                print('Failed to exit backend, rebooting aborted')

        elif code == 2:
            print(box('Failed to connect to CADENCE backend. You can try to use the start subcommand to start it'))

        elif code == 3:
            print(box('[Failed]: received an unexpected default response code from CADENCE backend which is not to be used under any circumstances. Please report this error'))

        elif code == 4:
            print(box('[Failed]: CADENCE backend is exiting'))

        if len(failed) > 0:
            lines = [f'There are failed actions ({len(failed)}):\n']
            lines += list(map(lambda x: f'  {x['msg']}', failed))
            print(box('\n'.join(lines)))

        print()
        return code

def _wrap_request(args):
    args['source'] = 'cli'
    args['cwd'] = str(Path.cwd())
    return args

def _start_backend(**kwargs):
    result = start(**kwargs)
    notifies = []
    if result is SENTINELS.BACKEND_STARTED:
        print(f'CADENCE backend is now up and running')
        notifies = send_request(**_wrap_request({'action':'get_notifies'})).get('notifies', [])
    elif result is SENTINELS.BACKEND_ALREADY_RUNNING:
        print(f'CADENCE backend is already running')
    elif result is SENTINELS.FAILED_START_BACKEND:
        print(f'Failed to start CADENCE backend')
    return result, notifies

def _show_notifies(notifies=None):
    if notifies is None:
        notifies = []

    if len(notifies) > 0:
        lines = [
            f'Notifies from CADENCE backend ({len(notifies)}):'
        ]
        lines += list(map(lambda x: f'  {x}', notifies))
        print(box('\n'.join(lines)))

def _show_song_info(info, empty_msg='No information to be shown', show_aliases=False, show_playlists=False, show_num=False, show_tech=False):
    if not isinstance(info, (list, tuple)):
        info = (info,)
    if len(info) > 0:
        for i, song in enumerate(info):
            output = SongOutput(song)

            if show_num:
                lines = [f'{i+1}. {output.display_name}']
            else:
                lines = [f'{output.display_name}']

            lines += [
                f'\nName: {output.name}',
                f'Artist: {output.artist}',
                f'Album: {output.album}',
                f'\nDuration: {output.duration}',
            ]

            if show_tech:
                lines += [
                    f'\nBitrate: {output.bitrate} kbps',
                    f'Sample Rate: {output.sample_rate}',
                    f'Channels: {output.channels}',
                ]

            lines += [
                f'\nPath: {output.path}',
                f'\nLibrary ID: {output.lib_id}'
            ]

            if show_aliases:
                lines += [f"\nAliases ({output.aliases_num}): {output.aliases}"]

            if show_playlists:
                lines += [f"\nPlaylists ({output.playlists_num}): {output.playlists}"]

            print(box('\n'.join(lines)))
    else:
        print(empty_msg)

if __name__ == '__main__':
    sys.exit(main())