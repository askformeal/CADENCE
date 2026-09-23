from src.config import CONFIG
from src.frontend.song_output import SongOutput
from src.utils.tui import box

def cli_box(*args, **kwargs):
    return box(*args, style=CONFIG.cli_box_style, **kwargs)

def show_notifies(notifies=None):
    if notifies is None:
        notifies = []

    if len(notifies) > 0:
        lines = [
            f'Notifies from CASCADE backend ({len(notifies)}):'
        ]
        lines += list(map(lambda x: f'  {x}', notifies))
        print(cli_box('\n'.join(lines)))

def show_option_info(info):
    name = info.get('name', 'N/A')
    type_ = info.get('type', 'N/A')
    value = info.get('value', 'N/A')
    source = info.get('source', 'N/A')
    default = info.get('default', 'N/A')
    description = info.get('description', 'No Description')
    
    lines = [
        f'Name: {name}',
        f'Type: {type_}',
        f'Value: {value}',
        f'Source: {source}',
        f'Default Value: {default}',
        f'\n\"{description}\"'
        ]
    print(cli_box('\n'.join(lines)))

def show_song_info(info, empty_msg='No information to be shown', show_aliases=False, show_playlists=False, show_num=False, show_tech=False):
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
                f'Lyric Offset: {output.lyric_offset}',
                f'\nLibrary ID: {output.lib_id}'
            ]

            if show_aliases:
                lines += [f"\nAliases ({output.aliases_num}): {output.aliases}"]

            if show_playlists:
                lines += [f"\nPlaylists ({output.playlists_num}): {output.playlists}"]

            print(cli_box('\n'.join(lines)))
    else:
        print(empty_msg)