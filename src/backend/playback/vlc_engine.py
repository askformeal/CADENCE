from time import sleep
import os
from pathlib import Path

env_lib = os.environ.get('PYTHON_VLC_LIB_PATH', None)
env_plugin = os.environ.get('PYTHON_VLC_MODULE_PATH', None)
if env_lib is not None and not Path(env_lib).is_file():
    vlc = None
    vlc_error = FileNotFoundError(f'PYTHON_VLC_LIB_PATH points to a missing file: \"{env_lib}\"')
elif env_plugin is not None and not Path(env_plugin).is_dir():
    vlc = None    
    vlc_error = FileNotFoundError(f'PYTHON_VLC_MODULE_PATH points to a missing directory: \"{env_plugin}\"')
else:
    try:
        import vlc
    except (Exception, SystemExit) as e:
        vlc = None
        vlc_error = e

from src.constants import PLAYER_POLL_INTERVAL
from src.config import CONFIG
from src.sentinels import SENTINELS
from src.error import InitializationError
from .engine import Engine

class VLCEngine(Engine):
    def __init__(self, logger, on_end_func):
        super().__init__(logger, 'VLC', on_end_func)
        if vlc is None:
            raise InitializationError(f'Failed to access VLC backend: {str(vlc_error)}') from vlc_error
        else:
            self.instance = vlc.Instance('--no-video')
            self.player = self.instance.media_player_new()
            self.medias = []
            self._attach_events()
            self.logger.debug(f'{__name__} initiated')

    def _attach_events(self):
        manager = self.player.event_manager() # I might need... Scratch that. I WILL need this.
        manager.event_attach(vlc.EventType.MediaPlayerEndReached, lambda *_: self.on_end())

    def _wait_state(self, target_states):
        for i in range(int(CONFIG.player_timeout/PLAYER_POLL_INTERVAL)):
            state = self.player.get_state()
            if state in target_states:
                return state
            elif state == vlc.State.Error:
                return state
            sleep(PLAYER_POLL_INTERVAL)
        self.logger.info('Timeout waiting for completion')
        return None

    def get_status(self):
        return {
            vlc.State.Playing: SENTINELS.PLAYING,
            vlc.State.Paused: SENTINELS.PAUSED,
            vlc.State.Stopped: SENTINELS.STOPPED
            }.get(self.player.get_state(), SENTINELS.PLAYER_INVALID)

    def get_media_len(self):
        return len(self.medias)

    def get_progress(self):
        length = self.player.get_length()
        time_ = self.player.get_time()
        return {'length': length, 'time': time_}

    def switch_prev(self):
        return self.load_number(self.number - 1)

    def switch_next(self):
        return self.load_number(self.number + 1)

    def load_number(self, num):
        if len(self.medias) > 0:
            if num < 0:
                self.number = len(self.medias) - 1
            elif num >= len(self.medias):
                self.number = 0
            else:
                self.number = num

            self.player.set_media(self.medias[self.number])
            return self.play()
        else:
            return SENTINELS.PLAYER_EMPTY

    def load_paths(self, paths):
        if not isinstance(paths, (list, tuple)):
            paths = [paths]

        if len(paths) == 0:
            self.logger.error('Can not load empty path list')
            return SENTINELS.PLAYER_LOAD_EMPTY
        else:
            self.medias = []
            for path in paths:
                media = self.instance.media_new(path)
                media.parse()
                if media.get_state() == vlc.State.Error or media.get_parsed_status() == vlc.MediaParsedStatus.failed:
                    self.logger.error(f'Failed to parse {path}')
                    break
                else:
                    self.medias.append(media)
            else:
                self.logger.info(f'Opened {len(paths)} files: {", ".join(paths)}')
                self.number = 0
                return self.load_number(0)                 

            self.medias = []
            return SENTINELS.ENGINE_ERROR

    def stop(self):
        self.player.stop()
        result = self._wait_state([vlc.State.Stopped])
        if result is None:
            return SENTINELS.PLAYER_TIMEOUT

        elif result == vlc.State.Stopped:
            self.logger.info('Stopped playing')
            return SENTINELS.SUCCESS
        
        elif result == vlc.State.Error:
            self.logger.error('Failed to stop playing')
            return SENTINELS.ENGINE_ERROR

    def jump_pos(self, pos):
        if self.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
            length = self.get_progress()['length']
            pos = int(pos)
            if pos > length:
                return SENTINELS.POS_TOO_LATE
            else:
                self.player.set_time(pos)
                return SENTINELS.SUCCESS
        else:
            return SENTINELS.INVALID_PLAYER_STATE

    def play(self):
        self.player.play()
        result = self._wait_state([vlc.State.Playing])
        if result is None:
            return SENTINELS.PLAYER_TIMEOUT

        elif result == vlc.State.Playing:
            self.logger.info('Started playing')
            self._apply_volume()
            return SENTINELS.SUCCESS
        
        elif result == vlc.State.Error:
            self.logger.error('Failed to start playing')
            return SENTINELS.ENGINE_ERROR

    def toggle(self):
        state = self.player.get_state()
        if state == vlc.State.Paused:
            return self.resume()
        elif state == vlc.State.Playing:
            return self.pause()
        else:
            self.logger.error('Invalid player state, can not toggle')
            return SENTINELS.INVALID_PLAYER_STATE

    def pause(self):
        if self.player.get_state() == vlc.State.Playing:
            self.player.set_pause(1)
            result = self._wait_state([vlc.State.Paused])
            if result is None:
                return SENTINELS.PLAYER_TIMEOUT

            elif result == vlc.State.Paused:
                self.logger.info('Paused')
                return SENTINELS.SUCCESS

            elif result == vlc.State.Error:
                self.logger.error('Failed to pause audio')
                return SENTINELS.ENGINE_ERROR
        else:
            self.logger.error('Failed to pause because player is not playing')
            return SENTINELS.INVALID_PLAYER_STATE

    def resume(self):
        if self.player.get_state() == vlc.State.Paused:
            self.player.set_pause(0)
            result = self._wait_state([vlc.State.Playing])
            if result is None:
                return SENTINELS.PLAYER_TIMEOUT
            elif result == vlc.State.Playing:
                self.logger.info('Resumed')
                return SENTINELS.SUCCESS

            elif result == vlc.State.Error:
                self.logger.info('Failed to resume audio')
                return SENTINELS.ENGINE_ERROR
        else:
            self.logger.error('Failed to resume because player is not paused')
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
        if self.player.get_state() in (vlc.State.Playing, vlc.State.Paused):
            self.logger.debug(f'Applied volume: {self.volume}, mute: {self.mute}')
            self.player.audio_set_volume(self.volume)
            self.player.audio_set_mute(self.mute)
        else:
            self.logger.debug(f'Can not apply volume and mute: unsupported player state')
        
    def on_exit(self):
        self.player.stop()
        self.instance.release()
        return SENTINELS.SUCCESS
