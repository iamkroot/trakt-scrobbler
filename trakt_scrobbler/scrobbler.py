import logging
from threading import Thread, Timer
import trakt_interface as trakt
from utils import read_json, write_json

logger = logging.getLogger('trakt_scrobbler')


class Scrobbler(Thread):
    """Scrobbles the data from queue to Trakt."""

    def __init__(self, scrobble_queue, watched_cache_clean_interval=3600):
        super().__init__(name='scrobbler')
        logger.info('Started scrobbler thread.')
        self.scrobble_queue = scrobble_queue
        self.watched_cache = read_json('watched_cache.json') or []
        self.watched_cache_clean_interval = watched_cache_clean_interval
        self.clear_watched_cache()

    def run(self):
        while True:
            scrobble_item = self.scrobble_queue.get()
            self.scrobble(*scrobble_item)
            self.scrobble_queue.task_done()

    def scrobble(self, verb, data):
        logger.debug(f'{data}')
        if trakt.scrobble(verb, **data):
            logger.info(f'Scrobble {verb} successful.')
        elif verb == 'stop' and data['progress'] > 80:
            logger.warning('Scrobble unsuccessful. Will try again later.')
            self.watched_cache.append(data)
            write_json(self.watched_cache, 'watched_cache.json')
        else:
            logger.warning('Scrobble unsuccessful.')

    def clear_watched_cache(self):
        self.watched_cache_timer = Timer(self.watched_cache_clean_interval,
                                         self.clear_watched_cache)
        self.watched_cache_timer.name = 'watched_cache_cleaner'
        self.watched_cache_timer.start()
        successful = []
        for item in self.watched_cache:
            logger.debug(f'{item}')
            if trakt.add_to_history(**item):
                logger.info('Successfully added media to history.')
                successful.append(item)
        for item in successful:
            self.watched_cache.remove(item)
        write_json(self.watched_cache, 'watched_cache.json')
