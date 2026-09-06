from . import playback, misc, config
from .library import library, meta, alias, lyric, playlist

ROUTER = {
    'test_alive': misc.test_alive,
    'get_notifies': misc.get_notifies,
    'status': playback.status,
    'open': playback.open,
    'play-all': playback.play_all,
    'continue_last': playback.continue_last,
    'stop': playback.stop,
    'pause': playback.pause,
    'resume': playback.resume,
    'toggle': playback.toggle,
    'list': playback.list_,
    'loop': playback.loop,
    'shuffle': playback.shuffle,
    'dice': playback.dice,
    'switch': playback.switch,
    'prev': playback.prev,
    'next': playback.next_,
    'seek': playback.seek,
    'jump': playback.jump,
    'replay': playback.replay,
    'volume': playback.volume,
    'mute': playback.mute,
    'lyric': playback.lyric,

    'lib.info': library.info,
    'lib.list': library.list_,
    'lib.search': library.search,
    'lib.add': library.add,
    'lib.del': library.del_,
    'lib.prune': library.prune,
    'lib.scan': library.scan,
    'lib.reset': library.reset,

    'lib.meta.set': meta.set_,
    'lib.meta.read-file': meta.read_file,

    'lib.alias.list': alias.list_,
    'lib.alias.bind': alias.bind,
    'lib.alias.unbind': alias.unbind,

    'lib.lyric.set': lyric.set_,
    'lib.lyric.show': lyric.show,
    'lib.lyric.fetch': lyric.fetch,

    'lib.playlist.list': playlist.list_,
    'lib.playlist.create': playlist.create,
    'lib.playlist.add': playlist.add,
    'lib.playlist.kick': playlist.kick,
    'lib.playlist.del': playlist.del_,

    'config.list': config.list_,
    'config.show': config.show,
    'config.set': config.set_,
    'config.unset': config.unset,
    'config.open': config.open_,
    'config.path': config.path,

    'exit': misc.exit_,
}