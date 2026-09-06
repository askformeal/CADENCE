import sys
from pathlib import Path
import readchar
from time import sleep

from src.config import CONFIG
from src.sentinels import SENTINELS
from src.frontend.client import send_request, test_alive
from src.process import start, kill
from src.constants import RESTART_NUM, RESTART_POLL_INTERVAL, ATTACHMENT_REQUIRED_ACTIONS
from src.config_manager import CONFIG_MANAGER
from src.frontend.song_output import SongOutput
from src.utils.tui import box
from src.utils.time_ import format_time
from .build_parser import build_parser

def main():
    is_reboot = False

    parser = build_parser()
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

    elif args['action'] == 'dash':
        from src.frontend.dash.core import Dash
        Dash().run()

    else:
        if args.get('meta_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['meta_action']}"
            del args['meta_action']

        if args.get('alias_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['alias_action']}"
            del args['alias_action']

        if args.get('lyric_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['lyric_action']}"
            del args['lyric_action']

        if args.get('playlist_action', None) is not None:
            args['lib_action'] = f"{args['lib_action']}.{args['playlist_action']}"
            del args['playlist_action']

        if args.get('lib_action', None) is not None:
            args['action'] = f"{args['action']}.{args['lib_action']}"
            del args['lib_action']

        if args.get('config_action', None) is not None:
            args['action'] = f"{args['action']}.{args['config_action']}"
            del args['config_action']

        if args['action'] == 'reboot':
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

        if args.get('direct', False):
            if args['action'] == 'config.list':
                response = CONFIG_MANAGER.get_all_option_info()
            elif args['action'] == 'config.show':
                response = CONFIG_MANAGER.get_option_info(args['option'])
            elif args['action'] == 'config.set':
                response = CONFIG_MANAGER.set_option_value(args['option'], args['value'], args['overwrite_corrupt'])
            elif args['action'] == 'config.unset':
                response = CONFIG_MANAGER.unset_option(args['option'])
            elif args['action'] == 'config.open':
                response = CONFIG_MANAGER.open_config_file()
            elif args['action'] == 'config.path':
                response = CONFIG_MANAGER.get_path()
            response = dict(response)
        else:
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
            print(_cli_box(f'[Succeeded]: {response['msg']}'))

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
                                        f'\n{output.display_name} - {output.artist} [{output.current_num} / {output.playlist_len}]',
                                        f'[{output.time} / {output.length}] {output.percentage}%\n',
                                        f'In library: {output.in_lib}',
                                        f'Album: {output.album}',
                                        f'Path: {output.path}\n',
                                        f'Lyric File Path: {output.lyric}',
                                        f'Player status: {output.player_status}',
                                        f'Volume: {output.volume}%',
                                        f'Mute: {output.mute}',
                                        f'\nShuffle: {output.shuffle}',
                                        f'Loop: {output.loop}',
                                        f'\nCADENCE backend has been running for {output.run_time}',
                        ))

                        if output.dev:
                            text += '\n\nDEVELOPMENT MODE ON'

                        print(_cli_box(text))

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

                    elif action == 'lib.lyric.show':
                        lines = [f"Path: {attachment.get('path', '?')}", '']
                        for timestamp, text in attachment.get('lyric', []):
                            lines.append(f"[{format_time(timestamp)}] {text.strip().replace('\n', ' \\ ')}")

                        print(_cli_box('\n'.join(lines)))

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
                    elif action == 'config.list':
                        for option_info in attachment:
                            _show_option_info(option_info)

                    elif action == 'config.show':
                        _show_option_info(attachment)

                    elif action == 'config.path':
                        print(_cli_box(attachment))

        elif code == 1:
            print(_cli_box(f'[Failed]: {response['msg']}'))
            if is_reboot:
                print('Failed to exit backend, rebooting aborted')

        elif code == 2:
            print(_cli_box('Failed to connect to CADENCE backend. You can try to use the start subcommand to start it'))

        elif code == 3:
            print(_cli_box('[Failed]: received an unexpected default response code from CADENCE backend which is not to be used under any circumstances. Please report this error'))

        elif code == 4:
            print(_cli_box('[Failed]: CADENCE backend is exiting'))

        elif code == 5:
            print(_cli_box('[Failed]: Token rejected, authorization failed'))

        else:
            print(_cli_box(f'[Failed]: Unknown response code \"{code}\"'))

        if len(failed) > 0:
            lines = [f'There are failed actions ({len(failed)}):\n']
            lines += list(map(lambda x: f'  {x['msg']}', failed))
            print(_cli_box('\n'.join(lines)))

        print()
        return code

def _wrap_request(args):
    args['source'] = 'cli'
    args['cwd'] = str(Path.cwd())
    args['notify_support'] = True
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

def _cli_box(*args, **kwargs):
    return box(*args, style=CONFIG.cli_box_style, **kwargs)

def _show_notifies(notifies=None):
    if notifies is None:
        notifies = []

    if len(notifies) > 0:
        lines = [
            f'Notifies from CADENCE backend ({len(notifies)}):'
        ]
        lines += list(map(lambda x: f'  {x}', notifies))
        print(_cli_box('\n'.join(lines)))

def _show_option_info(info):
    name = info.get('name', 'N/A')
    value = info.get('value', 'N/A')
    source = info.get('source', 'N/A')
    default = info.get('default', 'N/A')
    description = info.get('description', 'No Description')
    
    lines = [
        f'Name: {name}',
        f'Value: {value}',
        f'Source: {source}',
        f'Default Value: {default}',
        f'\n\"{description}\"'
        ]
    print(_cli_box('\n'.join(lines)))

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
                f'Lyric Path: {output.lyric}',
                f'\nLibrary ID: {output.lib_id}'
            ]

            if show_aliases:
                lines += [f"\nAliases ({output.aliases_num}): {output.aliases}"]

            if show_playlists:
                lines += [f"\nPlaylists ({output.playlists_num}): {output.playlists}"]

            print(_cli_box('\n'.join(lines)))
    else:
        print(empty_msg)

if __name__ == '__main__':
    sys.exit(main())