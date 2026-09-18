from dataclasses import dataclass
from typing import Callable

from src.backend.database.core import Database
from src.backend.playback.core import Playback

@dataclass
class Context:
    database: Database
    playback: Playback
    exit_: Callable
    start_time: int
    dev: bool