from abc import ABC, abstractmethod

from src.sentinels import Sentinel
from src.config import CONFIG

class Engine(ABC):
    def __init__(self, logger, on_end_func):
        self.logger = logger
        self.on_end = on_end_func
        self.number: int = 0
        self.volume: int = CONFIG.default_volume
        self.mute: bool = False

    @abstractmethod
    def get_status(self) -> Sentinel | None:
        ...

    @abstractmethod
    def get_media_len(self):
        ...

    @abstractmethod
    def get_progress(self) -> dict[str, int]:
        ...

    @abstractmethod
    def switch_prev(self) -> Sentinel:
        ...

    @abstractmethod
    def switch_next(self) -> Sentinel:
        ...

    @abstractmethod
    def load_number(self, num) -> Sentinel:
        ...

    @abstractmethod
    def load_paths(self, paths) -> Sentinel:
        ...

    @abstractmethod
    def stop(self) -> Sentinel:
        ...

    @abstractmethod
    def jump_pos(self, pos) -> Sentinel:
        ...

    @abstractmethod
    def play(self) -> Sentinel:
        ...

    @abstractmethod
    def toggle(self) -> Sentinel:
        ...

    @abstractmethod
    def pause(self) -> Sentinel:
        ...

    @abstractmethod
    def resume(self) -> Sentinel:
        ...

    @abstractmethod
    def set_volume(self, volume) -> Sentinel:
        ...

    @abstractmethod
    def set_mute(self, mute) -> Sentinel:
        ...
    
    @abstractmethod
    def on_exit(self) -> Sentinel:
        ...
