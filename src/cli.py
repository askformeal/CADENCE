import argparse
import sys
from pathlib import Path

from src.client import send_request

def _path(val):
    return str(Path(val).absolute())

parser = argparse.ArgumentParser()

command_sub = parser.add_subparsers(dest='action', required=True)

status_parser = command_sub.add_parser('status')
open_parser = command_sub.add_parser('open')
open_parser.add_argument('song', type=str)
pause_parser = command_sub.add_parser('pause')
resume_parser = command_sub.add_parser('resume')
toggle_parser = command_sub.add_parser('toggle')
stop_parser = command_sub.add_parser('stop')
prev_parser = command_sub.add_parser('prev')
next_parser = command_sub.add_parser('next')

lib_parser = command_sub.add_parser('lib')

lib_sub = lib_parser.add_subparsers(dest='lib_action', required=True)

lib_list_parser = lib_sub.add_parser('list')
lib_add_parser = lib_sub.add_parser('add')
lib_add_parser.add_argument('path', type=_path)
lib_del_parser = lib_sub.add_parser('del')
lib_del_parser.add_argument('song', type=str)

alias_parser = lib_sub.add_parser('alias')
alias_sub = alias_parser.add_subparsers(dest='alias_action', required=True)
alias_list_parser = alias_sub.add_parser('list')
alias_list_parser.add_argument('song', type=str)

alias_bind_parser = alias_sub.add_parser('bind')
alias_bind_parser.add_argument('song', type=str)
alias_bind_parser.add_argument('alias', type=str)

exit_parser = command_sub.add_parser('exit')

args = vars(parser.parse_args())

if args.get('alias_action') is not None:
    args['lib_action'] = f"{args['lib_action']}.{args['alias_action']}"
    del args['alias_action']

if args.get('lib_action', None) is not None:
    args['action'] = f'{args["action"]}.{args['lib_action']}'
    del args['lib_action']

args['cwd'] = str(Path.cwd())

response = send_request(**args)


if response['code'] == 0:
    print('Succeeded')
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
        for song in info:
            texts = [
                f'Path: {song["path"]}'
            ]
            max_len = max(map(len, texts))
            print('-'*(max_len))
            print(f'#{song["id"]}.')
            print('\n'.join(texts))
            print('-'*(max_len))
            print()

    elif args['action'] == 'lib.alias.list':
        aliases = response['attachment']
        print(aliases)

else:
    print(f'Failed: {response['msg']}')

sys.exit(response['code'])