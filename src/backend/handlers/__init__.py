from . import misc, config, poll
from .library import meta, alias, lyric, playlist
from .library import core as lib_core
from .playback import sequence, navigation
from .playback import core as play_core

ROUTER = {
    'test_alive': misc.test_alive,
    'get_notifies': misc.get_notifies,

    'status': play_core.status,
    'open': play_core.open,
    'play-all': play_core.play_all,
    'load_last': play_core.load_last,
    'stop': play_core.stop,
    'pause': play_core.pause,
    'resume': play_core.resume,
    'toggle': play_core.toggle,
    'list': sequence.list_,
    'loop': sequence.loop,
    'shuffle': sequence.shuffle,
    'dice': sequence.dice,
    'switch': sequence.switch,
    'prev': sequence.prev,
    'next': sequence.next_,
    'seek': navigation.seek,
    'jump': navigation.jump,
    'replay': navigation.replay,
    'volume': play_core.volume,
    'mute': play_core.mute,
    'lyric': play_core.lyric,
    'set_offset_overlay': play_core.set_offset_overlay,
    'poll': poll.poll,

    'lib.info': lib_core.info,
    'lib.list': lib_core.list_,
    'lib.search': lib_core.search,
    'lib.add': lib_core.add,
    'lib.del': lib_core.del_,
    'lib.prune': lib_core.prune,
    'lib.scan': lib_core.scan,
    'lib.reset': lib_core.reset,

    'lib.meta.set': meta.set_,
    'lib.meta.read-file': meta.read_file,

    'lib.alias.list': alias.list_,
    'lib.alias.bind': alias.bind,
    'lib.alias.unbind': alias.unbind,

    'lib.lyric.set': lyric.set_,
    'lib.lyric.show': lyric.show,
    'lib.lyric.fetch': lyric.fetch,
    'lib.lyric.offset': lyric.offset,

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