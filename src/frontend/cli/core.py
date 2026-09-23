import sys
from pathlib import Path
import readchar
from time import sleep

from src.sentinels import SENTINELS
from src.frontend.client import send_request, test_alive
from src.process import start, kill
from src.constants.process import RESTART_NUM, RESTART_POLL_INTERVAL
from src.constants.frontend import ATTACHMENT_REQUIRED_ACTIONS
from src.config_manager import CONFIG_MANAGER
from src.frontend.song_output import SongOutput
from src.utils.escape_code import ESCAPE_CODE as EC
from src.utils.time_ import format_time
from .build_parser import build_parser
from .translate import translate
from .show_info import (
    cli_box,
    show_notifies,
    show_option_info,
    show_song_info
    )

def main():
    is_reboot = False

    parser = build_parser()
    args = vars(parser.parse_args())
    args = translate(args)

    if args['action'] == 'start':
        notifies = _start_backend(CASCADE_DEV=int(args['dev']), CASCADE_CONTINUE=int(args['continue']))[1]
        show_notifies(notifies)

    elif args['action'] == 'kill':
        print(f'Killing CASCADE backend processes...')
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

        show_notifies(notifies)

        if code is None or msg is None:
            print('[Failed]: Invalid response received from CASCADE backend')

        elif code == 0:
            print(cli_box(f'{EC.bold}{EC.green}[Succeeded]{EC.rs}: {response['msg']}'))

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
                notifies = _start_backend(CASCADE_DEV=int(args['dev']), CASCADE_CONTINUE=int(args['continue']))[1]

                show_notifies(notifies)

            elif action == 'lib.add' and isinstance(attachment, list):
                for add_response in attachment:
                    print(add_response['msg'])

            elif action in ATTACHMENT_REQUIRED_ACTIONS:
                if attachment is None and not (action == 'lib.scan' and not args['dry_run']):
                    print(f'[Failed]: action {action} was expecting an attachment but none was received from CASCADE backend')
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
                                        f'Reverse: {output.reverse}',
                                        f'Online Lyric: {output.online_lyric}',
                                        f'\nAudio Engine: {output.engine}',
                                        f'\nCASCADE backend has been running for {output.run_time}',
                        ))

                        if output.dev:
                            text += '\n\nDEVELOPMENT MODE ON'

                        print(cli_box(text))

                    elif action == 'list':
                        show_song_info(attachment, 'No songs are being played', show_num=True)

                    elif action == 'lib.info':
                        show_song_info(attachment, 
                                        show_tech=True, 
                                        show_aliases=args['show_aliases'],
                                        show_playlists=args['show_playlists'])

                    elif action == 'lib.list':
                        show_song_info(attachment, 
                                        'No songs in library', 
                                        show_tech=args['show_tech'],
                                        show_aliases=args['show_aliases'], 
                                        show_playlists=args['show_playlists'])

                    elif action == 'lib.search':
                        show_song_info(attachment, 'No results to be shown')

                    elif action == 'lib.prune':
                        show_song_info(attachment, 'No songs to be shown')

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

                        print(cli_box('\n'.join(lines)))

                    elif action == 'lib.playlist.list':
                        if args['playlist'] is not None:
                            show_song_info(attachment, 
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
                            show_option_info(option_info)

                    elif action == 'config.show':
                        show_option_info(attachment)

                    elif action == 'config.path':
                        print(cli_box(attachment))

        elif code == 1:
            print(cli_box(f'{EC.bold}{EC.red}[Failed]{EC.rs}: {response['msg']}'))
            if is_reboot:
                print('Failed to exit backend, rebooting aborted')

        elif code == 2:
            print(cli_box(f'{EC.bold}{EC.red}[Failed]{EC.rs} Failed to connect to CASCADE backend. You can try to use the start subcommand to start it'))

        elif code == 3:
            print(cli_box(f'{EC.bold}{EC.red}[Failed]{EC.rs}: received an unexpected default response code from CASCADE backend which is not to be used under any circumstances. Please report this error'))

        elif code == 4:
            print(cli_box(f'{EC.bold}{EC.red}[Failed]{EC.rs}: CASCADE backend is exiting'))

        elif code == 5:
            print(cli_box(f'{EC.bold}{EC.red}[Failed]{EC.rs}: Token rejected, authorization failed'))

        else:
            print(cli_box(f'{EC.bold}{EC.red}[Failed]{EC.rs}: Unknown response code \"{code}\"'))

        if len(failed) > 0:
            lines = [f'{EC.red}There are failed actions ({len(failed)}):{EC.rs}\n']
            lines += list(map(lambda x: f'  {x['msg']}', failed))
            print(cli_box('\n'.join(lines)))

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
        print(f'CASCADE backend is now up and running')
        notifies = send_request(**_wrap_request({'action':'get_notifies'})).get('notifies', [])
    elif result is SENTINELS.BACKEND_ALREADY_RUNNING:
        print(f'CASCADE backend is already running')
    elif result is SENTINELS.FAILED_START_BACKEND:
        print(f'Failed to start CASCADE backend. Examine log files for more information')
    return result, notifies

if __name__ == '__main__':
    sys.exit(main())