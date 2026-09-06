from dataclasses import dataclass
from typing import Callable

from src.backend.database.core import Database
from src.backend.vlc_player import Player
from src.backend.playback import Playback

@dataclass
class Context:
    database: Database
    player: Player
    playback: Playback
    exit_: Callable
    start_time: int
    dev: bool