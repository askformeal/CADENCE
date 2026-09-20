import time
from pathlib import Path
from threading import Thread

import just_playback # basically a wrapped version of miniaudio
from just_playback.ma_result import MiniaudioError

from src.constants.backend import (
    PLAYER_END_POLL_INTERVAL as END_POLL_INTERVAL,
    PLAYER_END_REDUNDANCY as END_REDUNDANCY
    )
from src.sentinels import SENTINELS
from src.error import InitializationError
from .base_engine import BaseEngine

class MiniEngine(BaseEngine):
    def __init__(self, logger, on_end_func):
        super().__init__(logger, 'Miniaudio', on_end_func)
        self.running = True
        try:
            self.player = just_playback.Playback()
        except MiniaudioError as e:
            raise InitializationError(f'Failed to initialize Miniaudio engine: {str(e)}') from e
        else:
            self.at_end = False
            Thread(target=self.poll_end, daemon=True).start()
            self.logger.debug(f'{__name__} initiated')

    def get_status(self):
        if not self.player.active:
            return SENTINELS.STOPPED
        elif self.player.paused:
            return SENTINELS.PAUSED
        else:
            return SENTINELS.PLAYING
    def get_progress(self):
        if self.player.active:
            time_ = self.player.curr_pos * 1000
            length = self.player.duration * 1000
        else:
            time_ = -1
            length = -1

        return time_, length

    def load_number(self):
        self.at_end = False
        path = self.medias[self.number]
        if Path(path).is_file():
            try:
                self.player.load_file(path)
            except (MiniaudioError, FileNotFoundError):
                self.logger.warning(f'Failed to load file: \"{path}\"')
                return SENTINELS.FILE_IO_FAILED
            else:
                return SENTINELS.SUCCESS
        else:
            self.logger.warning(f'File not exist: \"{path}\"')
            return SENTINELS.FILE_IO_FAILED
        
    def load_paths(self, paths):
        self.medias = []
        for path in paths:
            if Path(path).is_file():
                self.medias.append(path)
            else:
                self.logger.warning(f'File not exist: \"{path}\"')
                self.medias = []
                return SENTINELS.FILE_IO_FAILED

        return SENTINELS.SUCCESS

    def stop(self):
        self.player.stop()
        return SENTINELS.SUCCESS

    def jump_pos(self, pos):
        self.player.seek(pos / 1000)
        length = self.get_progress()[1]
        if length - pos > END_REDUNDANCY:
            self.at_end = False
        return SENTINELS.SUCCESS

    def play(self):
        try:
            self.player.play()
        except MiniaudioError as e:
            self.logger.error(f'Failed to play: {e}')
            return SENTINELS.ENGINE_ERROR
        if self.player.active:
            self.apply_volume()
            return SENTINELS.SUCCESS
        else:
            self.logger.error(f'Failed to start playing')
            return SENTINELS.ENGINE_ERROR

    def pause(self):
        if self.player.playing:
            self.player.pause()
            return SENTINELS.SUCCESS
        else:
            self.logger.error('Failed to pause because player is not playing')
            return SENTINELS.INVALID_PLAYER_STATE

    def resume(self):
        if self.player.paused:
            self.player.resume()
            return SENTINELS.SUCCESS
        else:
            self.logger.error('Failed to resume because player is not paused')
            return SENTINELS.INVALID_PLAYER_STATE

    def apply_volume(self):
        if self.player.active:
            if self.mute:
                self.player.set_volume(0)
            else:
                self.player.set_volume(self.volume/100)
            self.logger.debug(f'Applied volume: {self.volume}, mute: {self.mute}')
        else:
            self.logger.debug(f'Can not apply volume and mute: unsupported player state')
        return SENTINELS.SUCCESS

    def on_exit(self):
        self.player.stop()
        self.running = False
        return SENTINELS.SUCCESS

    def poll_end(self):
        while self.running:
            try:
                if self.player.playing:
                    time_, length = self.get_progress()
                    if (
                        not self.at_end
                        and time_ > 0
                        and length > 0
                        and length - time_ < END_REDUNDANCY
                    ):
                        self.on_end()
                        self.at_end = True
            except Exception as e:
                self.logger.exception(f'An error occurred when polling end of audio')
            finally:
                time.sleep(END_POLL_INTERVAL)
            