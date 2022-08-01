import time
from enum import IntEnum
from threading import Lock, Thread

import confuse
import requests
from trakt_scrobbler import config, logger
from trakt_scrobbler.file_info import get_media_info
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.utils import AutoloadError, ResumableTimer

SCROBBLE_VERBS = ('stop', 'pause', 'start')


class State(IntEnum):
    Stopped = 0
    Paused = 1
    Playing = 2


class Transition:
    """Helper class containing common properties of a state change"""

    def __init__(self, prev, current):
        self.prev = prev
        self.current = current
        self._is_same_media = None

    def is_state_jump(self, from_: State, to: State) -> bool:
        return self.prev['state'] == from_ and self.current['state'] == to

    @property
    def from_playing_to_paused(self) -> bool:
        return (self.prev['state'] == State.Playing and 
                self.current['state'] == State.Paused)

    @property
    def is_same_media(self) -> bool:
        # cache this because it is called multiple times and is relatively expensive
        if self._is_same_media is None:
            self._is_same_media = self.current['media_info'] == self.prev['media_info']
        return self._is_same_media

    @property
    def state_changed(self) -> bool:
        return self.prev['state'] != self.current['state']

    @property
    def elapsed_realtime(self) -> float:
        return self.current['updated_at'] - self.prev['updated_at']

    @property
    def progress(self) -> float:
        return self.current['progress'] - self.prev['progress']

    @property
    def abs_progress(self) -> float:
        return abs(self.progress)


class Monitor(Thread):
    """Generic base class that polls the player for state changes,
     and sends the info to scrobble queue."""

    CONFIG_TEMPLATE = {
        # min percent jump to consider for scrobbling to trakt
        'skip_interval': confuse.Number(default=5),
        # min progress (in %) at which file should be opened for preview to be started
        'preview_threshold': confuse.Number(default=80),
        # in seconds. How long the monitor should wait to start sending scrobbles
        'preview_duration': confuse.Number(default=60),
        # in seconds. Max time elapsed between a "play->pause" transition to trigger
        # the "fast_pause" state
        'fast_pause_threshold': confuse.Number(default=1),
        # in seconds. How long the monitor should wait to start sending scrobbles
        'fast_pause_duration': confuse.Number(default=5),
    }

    def __new__(cls, *args, **kwargs):
        try:
            cls.inject_base_config()
            cls.config = cls.autoload_cfg()
        except AutoloadError as e:
            logger.warning(str(e))
            logger.error(f"Config value autoload failed for {cls.name}.")
            notify(f"Check log file. {e!s}", category="exception")
        except Exception:
            msg = f"Config value autoload failed for {cls.name}."
            logger.exception(msg)
            notify(f"{msg} Check log file.", category="exception")
        else:
            return super().__new__(cls)

    @classmethod
    def inject_base_config(cls):
        """Inject default values from base config to allow player-specific overrides"""
        base_config = config['players'].get(Monitor.CONFIG_TEMPLATE)
        base_template = confuse.as_template(base_config)
        template = getattr(cls, 'CONFIG_TEMPLATE', {})
        updated = {**base_template.subtemplates, **template}
        cls.CONFIG_TEMPLATE = updated

    @classmethod
    def autoload_cfg(cls):
        template = getattr(cls, 'CONFIG_TEMPLATE', None)
        monitor_cfg = config['players'][cls.name].get(template)
        assert monitor_cfg is not None
        auto_keys = {k for k, v in monitor_cfg.items() if v == "auto-detect"}
        if not auto_keys:
            return monitor_cfg
        try:
            loaders = getattr(cls, "read_player_cfg")(auto_keys)
        except AttributeError:
            raise AutoloadError(param=auto_keys,
                                extra_msg=f"Autoload not supported for {cls.name}.")
        except FileNotFoundError as e:
            raise AutoloadError(src=e.filename, extra_msg="File not found")

        while auto_keys:
            param = auto_keys.pop()
            try:
                param_loader = loaders[param]
            except KeyError:
                raise AutoloadError(param,
                                    extra_msg="Autoload not supported for this param")
            try:
                monitor_cfg[param] = param_loader()
                logger.debug(f"Autoloaded {cls.name} {param} = {monitor_cfg[param]}")
            except FileNotFoundError as e:
                raise AutoloadError(param, src=e.filename, extra_msg="File not found")
        return monitor_cfg

    def __init__(self, scrobble_queue):
        super().__init__()
        logger.info('Started monitor for ' + self.name)
        self.scrobble_queue = scrobble_queue
        self.skip_interval = self.config['skip_interval']
        self.preview_threshold = self.config['preview_threshold']
        self.preview_duration = self.config['preview_duration']
        self.fast_pause_threshold = self.config['fast_pause_threshold']
        self.fast_pause_duration = self.config['fast_pause_duration']
        self.is_running = False
        self.status = {}
        self.prev_state = {}
        self.preview = False
        self.fast_pause = False
        self.scrobble_buf = None
        self.lock = Lock()
        self.preview_timer: ResumableTimer = None
        self.fast_pause_timer: ResumableTimer = None

    def can_connect(self) -> bool:
        raise NotImplementedError

    @staticmethod
    def parse_status(status):
        if (
            'filepath' not in status and 'media_info' not in status
        ) or not status.get('duration'):
            return {}

        if 'filepath' in status:
            media_info = get_media_info(status['filepath'])
        else:
            media_info = status['media_info']

        if media_info is None:
            return {}

        ep = media_info.get('episode')
        if isinstance(ep, list):
            media_info = media_info.copy()
            num_eps = len(media_info['episode'])
            status['duration'] //= num_eps
            ep_num, status['position'] = divmod(status['position'], status['duration'])
            ep_num = int(ep_num)
            # handle case when pos >= duration, causing ep_num == num_eps
            if ep_num == num_eps:
                ep_num -= 1
                status['position'] = status['duration']
            media_info['episode'] = media_info['episode'][ep_num]
        elif isinstance(ep, str):
            media_info['episode'] = int(ep)

        progress = min(round(status['position'] * 100 / status['duration'], 2), 100)
        return {
            'state': status['state'],
            'progress': progress,
            'media_info': media_info,
            'updated_at': time.time(),
        }

    def decide_action(self, prev, current):
        """
        Decide what action(s) to take depending on the prev and current states.
        """

        if not prev and not current:
            return None
        transition = Transition(prev, current)
        if (
            not prev
            or not current
            or not transition.is_same_media
            or prev['state'] == State.Stopped
        ):
            # media changed
            if self.preview:
                yield 'exit_preview'
            elif prev and prev['state'] != State.Stopped:
                yield 'stop_previous'
            if self.fast_pause:
                yield 'exit_fast_pause'
            if current:
                if current['progress'] > self.preview_threshold:
                    yield 'enter_preview'
                elif (
                    not prev 
                    or not transition.is_same_media
                    or transition.state_changed
                    or transition.abs_progress > self.skip_interval
                ):
                    yield 'scrobble'
        elif transition.state_changed or transition.abs_progress > self.skip_interval:
            # state changed
            if self.preview:
                if current['state'] == State.Stopped:
                    yield 'exit_preview'
                elif transition.from_playing_to_paused:
                    yield 'pause_preview'
                elif current['state'] == State.Playing:
                    yield 'resume_preview'
                else:
                    yield 'invalid_state'
            elif self.fast_pause:
                if (
                    current['state'] == State.Stopped
                    or transition.abs_progress > self.skip_interval
                ):
                    yield 'scrobble'
                    yield 'exit_fast_pause'
                elif current['state'] == State.Paused:
                    yield 'clear_buf'
                elif current['state'] == State.Playing:
                    yield 'delayed_play'
            else:  # normal state
                yield 'scrobble'
                if (
                    transition.from_playing_to_paused
                    and transition.elapsed_realtime < self.fast_pause_threshold
                ):
                    yield 'enter_fast_pause'

    def scrobble_status(self, status):
        verb = SCROBBLE_VERBS[status['state']]
        self.scrobble_queue.put((verb, status))

    def delayed_scrobble(self, cleanup=None):
        logger.debug("Delayed scrobble")
        with self.lock:
            if self.scrobble_buf:
                logger.debug(self.scrobble_buf)
                self.scrobble_status(self.scrobble_buf)
            if cleanup:
                cleanup()

    def clear_timer(self, timer_name):
        timer = getattr(self, timer_name)
        if timer is not None:
            timer.cancel()
            setattr(self, timer_name, None)

    def exit_preview(self):
        logger.debug("Exiting preview")
        if self.preview:
            self.preview = False
            self.scrobble_buf = None
            self.clear_timer('preview_timer')

    def exit_fast_pause(self):
        logger.debug("Exiting fast_pause")
        if self.fast_pause:
            self.fast_pause = False
            self.scrobble_buf = None
            self.clear_timer('fast_pause_timer')

    def scrobble_if_state_changed(self, prev, current):
        """
        Possible race conditions:
        1) start_preview, after __preview_duration__ secs, stop_preview
           start_preview starts preview_timer for " secs, with cleanup=exit_preview.
           the stop_preview also triggers exit_preview, both are run parallelly.
        """
        for action in self.decide_action(prev, current):
            logger.debug(f"action={action}")
            if action == "scrobble":
                logger.debug(current)
                self.scrobble_status(current)
            elif action == "stop_previous":
                self.scrobble_queue.put(("stop", prev))
            elif action == "exit_preview":
                self.exit_preview()
            elif action == "enter_preview":
                assert not self.preview and not self.scrobble_buf, "Invalid state"
                self.preview = True
                self.scrobble_buf = current
                self.preview_timer = ResumableTimer(
                    self.preview_duration, self.delayed_scrobble, (self.exit_preview,)
                )
                self.preview_timer.start()
            elif action == "pause_preview":
                self.scrobble_buf = current
                self.preview_timer.pause()
            elif action == "resume_preview":
                self.scrobble_buf = current
                self.preview_timer.resume()
            elif action == "enter_fast_pause":
                assert not self.fast_pause, "Invalid state"
                self.fast_pause = True
            elif action == "clear_buf":
                self.clear_timer('fast_pause_timer')
                self.scrobble_buf = None
            elif action == "delayed_play":
                self.clear_timer('fast_pause_timer')
                self.scrobble_buf = current
                self.fast_pause_timer = ResumableTimer(
                    self.fast_pause_duration,
                    self.delayed_scrobble,
                    (self.exit_fast_pause,),
                )
                self.fast_pause_timer.start()
            elif action == "exit_fast_pause":
                self.exit_fast_pause()
            else:
                logger.warning(f"Invalid action {action}")

    def handle_status_update(self):
        current_state = self.parse_status(self.status)
        with self.lock:
            self.scrobble_if_state_changed(self.prev_state, current_state)
        self.prev_state = current_state


class WebInterfaceMon(Monitor):
    """Base monitor for players with web interfaces that expose its state."""

    def __init__(self, scrobble_queue):
        super().__init__(scrobble_queue)
        self.sess = requests.Session()
        self.poll_interval = self.config['poll_interval']

    def can_connect(self) -> bool:
        try:
            self.update_status()
        except requests.ConnectionError:
            logger.debug(
                f'Unable to connect to {self.name}. Ensure that '
                f'the web interface is running.'
            )
            return False
        except requests.HTTPError as e:
            logger.debug(f"Error while getting data from {self.name}: {e}")
            return False
        else:
            return True

    def update_status(self):
        raise NotImplementedError

    def run(self):
        while True:
            try:
                self.update_status()
            except requests.ConnectionError:
                logger.info(
                    f'Unable to connect to {self.name}. Ensure that '
                    'the web interface is running.'
                )
                self.status = {}
            except requests.HTTPError as e:
                logger.error(f"Error while getting data from {self.name}: {e}")
                notify(f"Error while getting data from {self.name}: {e}",
                       category="exception")
                break
            if not self.status.get("filepath") and not self.status.get("media_info"):
                self.status = {}
            self.handle_status_update()
            time.sleep(self.poll_interval)

        logger.warning(f"{self.name} monitor stopped")
