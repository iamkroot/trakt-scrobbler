import time
import logging
import requests
from threading import Thread
from utils import config
from file_info import get_media_info

logger = logging.getLogger('trakt_scrobbler')


class Monitor(Thread):
    """Generic base class that polls the player for state changes,
     and puts the info to scrobble queue."""

    def __init__(self, scrobble_queue):
        super().__init__(name=self.name + 'mon')
        logger.info('Started monitor for ' + self.name)
        self.scrobble_queue = scrobble_queue
        self.is_running = False
        self.reset_status()
        self.prev_values = self.status.copy()
        self.watched_vars = ['state', 'filepath']

    def reset_status(self):
        self.status = {
            'state': 0,
            'position': 0,
            'duration': 0,
            'filepath': None
        }

    def state_changed(self):
        return any(self.prev_values[key] != self.status[key]
                   for key in self.watched_vars)

    def send_to_queue(self):
        data = {'player': self.name, 'time': time.time()}

        if self.is_running and self.status['filepath']:
            for key, value in self.status.items():
                if key != 'filepath':
                    data[key] = value
                else:
                    data['media_info'] = get_media_info(value)
        logger.debug(data)
        self.scrobble_queue.put(data)


class WebInterfaceMon(Monitor):
    """Base monitor for players with web interfaces that expose its state."""

    def __init__(self, scrobble_queue):
        super().__init__(scrobble_queue)
        self.sess = requests.Session()
        self.poll_interval = config['players'][self.name]['poll_interval']

    def can_connect(self):
        try:
            self.sess.head(self.URL)
        except requests.ConnectionError:
            logger.info(f'Unable to connect to {self.name}. ' +
                        'Ensure that the web interface is running.')
            self.is_running = False
        else:
            self.is_running = True
        return self.is_running

    def run(self):
        while True:
            if self.can_connect():
                self.update_status()
            else:
                self.reset_status()
            if self.state_changed():
                self.send_to_queue()
                self.prev_values = self.status.copy()
            time.sleep(self.poll_interval)
