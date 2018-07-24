import time
import logging
from threading import Thread
from file_info import get_data

logger = logging.getLogger('trakt_scrobbler')


class Monitor(Thread):
    """Generic class that polls the player for state changes,
     and puts the info to scrobble queue."""

    def __init__(self, player, scrobble_queue, poll_interval=10):
        super().__init__(name=player.name)
        logger.info('Started monitor for', player.name)
        self.player = player
        self.scrobble_queue = scrobble_queue
        self.poll_interval = poll_interval
        self.set_prev_values()

    def set_prev_values(self):
        self.prev_values = {
            'state': self.player.state,
            'file_path': self.player.file_path
        }

    def state_changed(self):
        return self.prev_values['state'] != self.player.state or \
            self.prev_values['file_path'] != self.player.file_path

    def run(self):
        while True:
            self.player.update_status()
            if self.state_changed():
                logger.debug('state_changed')
                self.send_to_queue()
                self.set_prev_values()
            time.sleep(self.poll_interval)

    def send_to_queue(self):
        # if player is stopped, send a dummy entry to the queue
        if not self.player.is_running or not self.player.file_path:
            data = {
                'player': self.player.name,
                'state': -1,
                'time': time.time()
            }
        else:
            data = {
                'file_info': get_data(self.player.file_path),
                'player': self.player.name,
                'position': self.player.position,
                'progress': self.player.progress,
                'duration': self.player.duration,
                'state': self.player.state,
                'time': time.time()
            }
        self.scrobble_queue.put(data)
