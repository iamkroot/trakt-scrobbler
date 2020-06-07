import time
import requests
from threading import Thread
from trakt_scrobbler import config, logger
from trakt_scrobbler.file_info import get_media_info
from trakt_scrobbler.utils import AutoloadError

SCROBBLE_VERBS = ('stop', 'pause', 'start')


class Monitor(Thread):
    """Generic base class that polls the player for state changes,
     and sends the info to scrobble queue."""

    def __new__(cls, *args, **kwargs):
        try:
            cls.config = cls.autoload_cfg()
        except AutoloadError as e:
            logger.debug(str(e))
            logger.error(f"Config value autoload failed for {cls.name}.")
        except Exception:
            logger.exception(f"Config value autoload failed for {cls.name}.")
        else:
            return super().__new__(cls)

    @classmethod
    def autoload_cfg(cls):
        template = getattr(cls, "CONFIG_TEMPLATE", None)
        monitor_cfg = config['players'][cls.name].get(template)
        auto_keys = {k for k, v in monitor_cfg.items() if v == "auto-detect"}
        if not auto_keys:
            return monitor_cfg
        try:
            loaders = getattr(cls, "read_player_cfg")(auto_keys)
        except AttributeError:
            logger.debug(f"Auto val not found for {', '.join(auto_keys)}")
            logger.error(f"Autoload not supported for {cls.name}.")
            raise AutoloadError
        while auto_keys:
            param = auto_keys.pop()
            try:
                param_loader = loaders[param]
            except KeyError:
                logger.error(f"Autoload not supported for '{param}'.")
                raise AutoloadError(param)
            try:
                monitor_cfg[param] = param_loader()
                logger.debug(f"Autoloaded {cls.name} {param} = {monitor_cfg[param]}")
            except FileNotFoundError as e:
                logger.error(f"File not found: {e.filename}")
                raise AutoloadError(src=e.filename)
        return monitor_cfg

    def __init__(self, scrobble_queue):
        super().__init__()
        logger.info('Started monitor for ' + self.name)
        self.scrobble_queue = scrobble_queue
        self.is_running = False
        self.status = {}
        self.prev_state = {}
        self.skip_interval = self.config.get('skip_interval', 5)

    def parse_status(self):
        if (
            'filepath' not in self.status and 'media_info' not in self.status
        ) or not self.status.get('duration'):
            return {}

        if 'filepath' in self.status:
            media_info = get_media_info(self.status['filepath'])
        else:
            media_info = self.status['media_info']

        if media_info is None:
            return {}

        ep = media_info.get('episode')
        if isinstance(ep, list):
            media_info = media_info.copy()
            num_eps = len(media_info['episode'])
            self.status['duration'] = self.status['duration'] // num_eps
            ep_num = int(self.status['position'] // self.status['duration'])
            media_info['episode'] = media_info['episode'][ep_num]
            self.status['position'] %= self.status['duration']
        elif isinstance(ep, str):
            media_info['episode'] = int(ep)

        progress = min(round(self.status['position'] * 100 /
                             self.status['duration'], 2), 100)
        return {
            'state': self.status['state'],
            'progress': progress,
            'media_info': media_info,
            'updated_at': time.time()
        }

    def scrobble_if_state_changed(self, prev, current):
        if not prev and not current:
            return
        if (not current and (not prev or prev['state'] != 0)) or \
           (prev and current and prev['state'] != 0 and
                prev['media_info'] != current['media_info']):
            self.scrobble_queue.put(('stop', prev))
        if not prev or \
           (current and (prev['state'] != current['state'] or
                         prev['media_info'] != current['media_info'] or
                         current['progress'] - prev['progress'] >
                         self.skip_interval)):
            verb = SCROBBLE_VERBS[current['state']]
            self.scrobble_queue.put((verb, current))

    def handle_status_update(self):
        current_state = self.parse_status()
        self.scrobble_if_state_changed(self.prev_state, current_state)
        self.prev_state = current_state


class WebInterfaceMon(Monitor):
    """Base monitor for players with web interfaces that expose its state."""

    def __init__(self, scrobble_queue):
        super().__init__(scrobble_queue)
        self.sess = requests.Session()
        self.poll_interval = self.config['poll_interval']

    def update_status(self):
        raise NotImplementedError

    def run(self):
        while True:
            try:
                self.update_status()
            except requests.ConnectionError:
                logger.info(f'Unable to connect to {self.name}. Ensure that '
                            'the web interface is running.')
                self.status = {}
            if not self.status.get("filepath") and not self.status.get("media_info"):
                self.status = {}
            self.handle_status_update()
            time.sleep(self.poll_interval)
