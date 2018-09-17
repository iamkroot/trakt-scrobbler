import time
import logging
import requests
from threading import Thread
from utils import config
from file_info import get_media_info

logger = logging.getLogger('trakt_scrobbler')
SCROBBLE_VERBS = ('stop', 'pause', 'start')


class Monitor(Thread):
    """Generic base class that polls the player for state changes,
     and puts the info to scrobble queue."""

    def __init__(self, scrobble_queue):
        super().__init__(name=self.name + 'mon')
        logger.info('Started monitor for ' + self.name)
        self.scrobble_queue = scrobble_queue
        self.is_running = False
        self.status = {}
        self.prev_state = {}
        self.watched_vars = ['state', 'filepath']

    def parse_status(self):
        if 'filepath' not in self.status or not self.status.get('duration'):
            return {}

        media_info = get_media_info(self.status['filepath'])
        if media_info is None:
            return {}

        if 'episode' in media_info and isinstance(media_info['episode'], list):
            num_eps = len(media_info['episode'])
            self.status['duration'] = self.status['duration'] // num_eps
            ep_num = int(self.status['position'] // self.status['duration'])
            media_info['episode'] = media_info['episode'][ep_num]
            self.status['position'] %= self.status['duration']

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
        if not current or \
           (prev and prev['media_info'] != current['media_info'] and
                prev['state'] != 0):
            self.scrobble_queue.put(('stop', prev))
        if not prev or \
           (current and (prev['state'] != current['state'] or
                         prev['media_info'] != current['media_info'] or
                         current['progress'] - prev['progress'] > 10)):
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
        self.poll_interval = config['players'][self.name]['poll_interval']

    def run(self):
        while True:
            try:
                self.update_status()
            except (requests.ConnectionError, requests.ConnectTimeout):
                logger.info(f'Unable to connect to {self.name}. Ensure that '
                            'the web interface is running.')
                self.status = {}
            self.handle_status_update()
            time.sleep(self.poll_interval)
