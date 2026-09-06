def gen_info_text(snapshot):
    lines = [
        'Information\n',
        f'Duration: {snapshot.duration}',
        '',
        f'Name: {snapshot.meta_name}',
        f'Artist: {snapshot.artist}',
        f'Album: {snapshot.album}',
        '',
        f'Bitrate: {snapshot.bitrate} kbps',
        f'Sample Rate: {snapshot.sample_rate}',
        f'Channels: {snapshot.channels}',
        '',
        'Aliases:',
        f'  {'\n  '.join(snapshot.aliases)}',
        '',
        'Playlists:',
        f'  {'\n  '.join(snapshot.added_playlists)}'
    ]

    text = '\n'.join(lines)

    return text