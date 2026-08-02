import logging
import vlc
from time import sleep
from src.constants import PLAYER_TIMEOUT, PLAYER_POLL_INTERVAL
from src.response import response_template
from src.sentinels import SENTINELS

logger = logging.getLogger(__name__)
class Player():
    def __init__(self, buffer_func):
        self.buffer = buffer_func
        self.instance = vlc.Instance('--no-video')
        self.player = self.instance.media_player_new()
        self.medias = []
        self.number = 0
        self._attach_events()

    def _attach_events(self):
        manager = self.player.event_manager() # I might need. Scratch that. I WILL need this.
        manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end)

    def _on_end(self, event):
        self.buffer({'action':'next'})

    def get_progress(self):
        length = self.player.get_length()
        time = self.player.get_time()
        return {'length': length, 'time': time}

    def switch_prev(self):
        return self.load_number(self.number - 1)

    def switch_next(self):
        return self.load_number(self.number + 1)

    def load_number(self, num):
        if len(self.medias) > 0:
            if num < 0:
                self.number = 0
            elif num >= len(self.medias):
                self.number = len(self.medias) - 1
            else:
                self.number = num

            self.player.set_media(self.medias[self.number])
            return self.play()
        else:
            return response_template.SWITCH_FAILED

    def load_paths(self, paths):
        if not isinstance(paths, (list, tuple)):
            paths = [paths]

        if len(paths) == 0:
            logger.error('Can not load empty path list')
            return response_template.EMPTY_PATHS
        else:
            self.medias = []
            for path in paths:
                media = self.instance.media_new(path)
                media.parse()
                if media.get_state() == vlc.State.Error or media.get_parsed_status() == vlc.MediaParsedStatus.failed:
                    logger.error(f'Failed to parse {path}')
                    break
                else:
                    self.medias.append(media)
            else:
                logger.info(f'Opened {len(paths)} files: {", ".join(paths)}')
                self.number = 0
                self.player.set_media(self.medias[0])
                return self.play()

            self.medias = []
            return response_template.VLC_ERROR

    def stop(self):
        self.player.stop()
        result = self._wait_state([vlc.State.Stopped])
        if result is None:
            return response_template.EVENT_TIMEOUT

        elif result == vlc.State.Stopped:
            logger.info('Stopped playing')
            return response_template.SUCCESS
        
        elif result == vlc.State.Error:
            logger.error('Failed to stop playing')
            return response_template.VLC_ERROR

    def _wait_state(self, target_states):
        for _ in range(int(PLAYER_TIMEOUT/PLAYER_POLL_INTERVAL)):
            state = self.player.get_state()
            if state in target_states:
                return state
            elif state == vlc.State.Error:
                return state
            sleep(PLAYER_POLL_INTERVAL)
        logger.info('Timeout waiting for completion')
        return None

    def play(self):
        self.player.play()
        result = self._wait_state([vlc.State.Playing])
        if result is None:
            return response_template.EVENT_TIMEOUT

        elif result == vlc.State.Playing:
            logger.info('Started playing')
            return response_template.SUCCESS
        
        elif result == vlc.State.Error:
            logger.error('Failed to start playing')
            return response_template.VLC_ERROR

    def toggle(self):
        state = self.player.get_state()
        if state == vlc.State.Paused:
            return self.resume()
        elif state == vlc.State.Playing:
            return self.pause()
        else:
            logger.error('Invalid player state, can not toggle')
            return response_template.TOGGLE_FAILED

    def pause(self):
        if self.player.get_state() == vlc.State.Playing:
            self.player.set_pause(1)
            result = self._wait_state([vlc.State.Paused])
            if result is None:
                return response_template.EVENT_TIMEOUT

            elif result == vlc.State.Paused:
                logger.info('Paused')
                return response_template.SUCCESS

            elif result == vlc.State.Error:
                logger.error('Failed to pause audio')
                return response_template.VLC_ERROR
        else:
            logger.error('Can not pause because player is not playing')
            return response_template.PAUSE_FAILED

    def resume(self):
        if self.player.get_state() == vlc.State.Paused:
            self.player.set_pause(0)
            result = self._wait_state([vlc.State.Playing])
            if result is None:
                return response_template.EVENT_TIMEOUT
            elif result == vlc.State.Playing:
                logger.info('Resumed')
                return response_template.SUCCESS

            elif result == vlc.State.Error:
                logger.info('Failed to resume audio')
                return response_template.VLC_ERROR
        else:
            logger.error('Can not resume because player is not paused')
            return response_template.RESUME_FAILED

    def on_exit(self):
        self.player.stop()
        self.instance.release()