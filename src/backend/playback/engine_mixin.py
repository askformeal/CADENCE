from .logger import logger
from src.config import CONFIG
from src.sentinels import SENTINELS
from .base_engine import BaseEngine
from .vlc_engine import VLCEngine
from .mini_engine import MiniEngine


class EngineMixin:
    def __init__(self):
        engine = {
            'vlc': VLCEngine,
            'miniaudio': MiniEngine
        }[CONFIG.engine]
        self.engine: BaseEngine = engine(logger, self.on_end) # PRIVATE PROPERTY. No underscore prefix because I'm lazy

    def get_engine_name(self):
        return self.engine.name
    
    def get_volume(self):
        return self.engine.volume
    
    def get_mute(self):
        return self.engine.mute
    
    def get_number(self):
        return self.engine.number
    
    def get_status(self):
        return self.engine.get_status()
    
    def get_progress(self):
        time_, length = self.engine.get_progress()
        if time_ < 0:
            time_ = -1
        time_ = round(time_)
    
        if length < 0:
            length = -1
        length = round(length)
    
        return {'time': time_, 'length': length}
    
    def get_media_len(self):
        return len(self.engine.medias)
    
    def load_paths(self, paths):
        if not isinstance(paths, (list, tuple)):
            paths = [paths]
    
        if len(paths) == 0:
            logger.error('Can not load empty path list')
            return SENTINELS.PLAYER_LOAD_EMPTY
        else:
            logger.info(f'Load {len(paths)} files: {", ".join(paths)}')
            result = self.engine.load_paths(paths)
            if result is SENTINELS.SUCCESS:
                return self.switch_to(0)
            else:
                return result
    
    def switch_to(self, num):
        media_len = len(self.engine.medias)
        if media_len > 0:
            if num < 0:
                self.engine.number = media_len - 1
            elif num >= media_len:
                self.engine.number = 0
            else:
                self.engine.number = num
            result = self.engine.load_number()
            if result is SENTINELS.SUCCESS:
                return self.engine.play()
            else:
                return result
        else:
            return SENTINELS.PLAYER_EMPTY
    
    def switch_prev(self):
        return self.switch_to(self.engine.number - 1)
    
    def switch_next(self):
        return self.switch_to(self.engine.number + 1)
    
    def pause(self):
        if self.engine.get_status() is SENTINELS.PLAYING:
            return self.engine.pause()
        else:
            logger.error('Failed to pause because player is not playing')
            return SENTINELS.INVALID_PLAYER_STATE
    
    def resume(self):
        if self.engine.get_status() is SENTINELS.PAUSED:
            return self.engine.resume()
        else:
            logger.error('Failed to resume because player is not paused')
            return SENTINELS.INVALID_PLAYER_STATE
    
    def toggle(self):
        status = self.engine.get_status()
        if status is SENTINELS.PLAYING:
            return self.pause()
        elif status is SENTINELS.PAUSED:
            return self.resume()
        else:
            logger.error('Invalid player state, can not toggle')
            return SENTINELS.INVALID_PLAYER_STATE
    
    def jump_pos(self, pos):
        if self.engine.get_status() in (SENTINELS.PLAYING, SENTINELS.PAUSED):
            length = self.engine.get_progress()[1]
            pos = int(pos)
            if pos > length:
                return SENTINELS.POS_TOO_LATE
            else:
                return self.engine.jump_pos(pos)
        else:
            return SENTINELS.INVALID_PLAYER_STATE
    
    def stop(self):
        return self.engine.stop()
    
    def set_volume(self, volume):
        self.engine.volume = volume
        logger.debug(f'Set target volume to {self.engine.volume}')
        return self.engine.apply_volume()
    
    def set_mute(self, mute):
        self.engine.mute = mute
        logger.debug(f'Set target mute mode to {self.engine.mute}')
        return self.engine.apply_volume()
    
    def on_end(self):
        if self.reverse:
            self.buffer({'action':'prev', 'on_end': True, 'source': 'player'})
        else:
            self.buffer({'action':'next', 'on_end': True, 'source': 'player'})