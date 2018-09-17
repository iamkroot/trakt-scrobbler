import logging
from threading import Thread
import trakt_interface as trakt
from utils import config

logger = logging.getLogger('trakt_scrobbler')
MONITORED_PLAYERS = config['players']['monitored']


class Scrobbler(Thread):
    """Scrobbles the data from queue to Trakt."""

    def __init__(self, scrobble_queue):
        super().__init__(name='scrobbler')
        logger.info('Started scrobbler thread.')
        self.scrobble_queue = scrobble_queue
        self.player_states = {name: {} for name in MONITORED_PLAYERS}

    def run(self):
        while True:
            scrobble_item = self.scrobble_queue.get()
            self.scrobble(*scrobble_item)
            self.scrobble_queue.task_done()

    def scrobble(self, verb, data):
        logger.debug(f'{data}')
        if trakt.scrobble(verb, **data):
            logger.info(f'Scrobble {verb} successful.')
            return True
        else:
            logger.warning('Scrobble unsuccessful.')
