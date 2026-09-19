import time
from pathlib import Path
from threading import Thread

import just_playback # basically a wrapped version of miniaudio
from just_playback.ma_result import MiniaudioError

from src.constants import (
    PLAYER_END_POLL_INTERVAL as END_POLL_INTERVAL,
    PLAYER_END_REDUNDANCY as END_REDUNDANCY
    )
from src.sentinels import SENTINELS
from src.error import InitializationError
from .engine import Engine

class MiniEngine(Engine):
    def __init__(self, logger, on_end_func):
        super().__init__(logger, 'Miniaudio', on_end_func)
        self.running = True
        try:
            self.player = just_playback.Playback()
        except MiniaudioError as e:
            raise InitializationError(f'Failed to initialize Miniaudio engine: {str(e)}') from e
        else:
            self.medias = []
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

    def get_media_len(self):
        return len(self.medias)

    def get_progress(self):
        if self.player.active:
            time_ = self.player.curr_pos
            if time_ > 0:
                time_ = round(time_ * 1000)
            time_ = int(time_)

            length = self.player.duration
            if length > 0:
                length = round(length * 1000)
            length = int(length)
        else:
            time_ = -1
            length = -1

        return {'length': length, 'time': time_}

    def load_number(self, num):
        self.at_end = False
        if len(self.medias) > 0:
            if num < 0:
                self.number = len(self.medias) - 1
            elif num >= len(self.medias):
                self.number = 0
            else:
                self.number = num
            path = self.medias[self.number]
            if Path(path).is_file():
                try:
                    self.player.load_file(path)
                except (MiniaudioError, FileNotFoundError):
                    self.logger.warning(f'Failed to load file: \"{path}\"')
                    return SENTINELS.FILE_IO_FAILED
                else:
                    return self.play()
            else:
                self.logger.warning(f'File not exist: \"{path}\"')
                return SENTINELS.FILE_IO_FAILED
        else:
            return SENTINELS.PLAYER_EMPTY
    
    def switch_prev(self):
        return self.load_number(self.number - 1)

    def switch_next(self):
        return self.load_number(self.number + 1)

    def load_paths(self, paths):
        if not isinstance(paths, (list, tuple)):
            paths = [paths]

        if len(paths) == 0:
            self.logger.error('Can not load empty path list')
            return SENTINELS.PLAYER_LOAD_EMPTY
        else:
            self.medias = []
            for path in paths:
                if Path(path).is_file():
                    self.medias.append(path)
                else:
                    self.logger.warning(f'File not exist: \"{path}\"')
                    break
            else:
                self.logger.info(f'Loaded {len(paths)} files: {", ".join(paths)}')
                self.number = 0
                return self.load_number(0)

            self.medias = []
            return SENTINELS.FILE_IO_FAILED

    def stop(self):
        self.player.stop()
        return SENTINELS.SUCCESS

    def jump_pos(self, pos):
        if self.player.active:
            length = self.get_progress()['length']
            pos = int(pos)
            if pos > length:
                return SENTINELS.POS_TOO_LATE
            else:
                self.player.seek(pos / 1000)
                if length - pos > END_REDUNDANCY:
                    self.at_end = False
                return SENTINELS.SUCCESS
        else:
            return SENTINELS.INVALID_PLAYER_STATE

    def play(self):
        try:
            self.player.play()
        except MiniaudioError as e:
            self.logger.error(f'Failed to play: {e}')
            return SENTINELS.ENGINE_ERROR
        if self.player.active:
            self._apply_volume()
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

    def toggle(self):
        if self.player.playing:
            self.pause()
            return SENTINELS.SUCCESS
        elif self.player.paused:
            self.resume()
            return SENTINELS.SUCCESS
        else:
            self.logger.error('Invalid player state, can not toggle')
            return SENTINELS.INVALID_PLAYER_STATE

    def set_volume(self, volume):
        self.volume = volume
        self.logger.debug(f'Set target volume to {self.volume}')
        self._apply_volume()
        return SENTINELS.SUCCESS

    def set_mute(self, mute):
        self.mute = mute
        self.logger.debug(f'Set target mute mode to {self.mute}')
        self._apply_volume()
        return SENTINELS.SUCCESS

    def _apply_volume(self):
        if self.player.active:
            if self.mute:
                self.player.set_volume(0)
            else:
                self.player.set_volume(self.volume/100)
            self.logger.debug(f'Applied volume: {self.volume}, mute: {self.mute}')
        else:
            self.logger.debug(f'Can not apply volume and mute: unsupported player state')

    def on_exit(self):
        self.player.stop()
        self.running = False
        return SENTINELS.SUCCESS

    def poll_end(self):
        while self.running:
            try:
                if self.player.playing:
                    progress = self.get_progress()
                    time_ = progress['time']
                    length = progress['length']
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
            