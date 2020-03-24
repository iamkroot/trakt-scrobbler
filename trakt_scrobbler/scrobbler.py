from threading import Thread, Timer
from trakt_scrobbler import logger
from trakt_scrobbler import trakt_interface as trakt
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.utils import read_json, write_json

WATCHED_CACHE_PATH = DATA_DIR / 'watched_cache.json'


class Scrobbler(Thread):
    """Scrobbles the data from queue to Trakt."""

    def __init__(self, scrobble_queue, watched_cache_clean_interval=3600):
        super().__init__(name='scrobbler')
        logger.info('Started scrobbler thread.')
        self.scrobble_queue = scrobble_queue
        self.watched_cache = read_json(WATCHED_CACHE_PATH) or []
        self.watched_cache_clean_interval = watched_cache_clean_interval
        self.clear_watched_cache()

    def run(self):
        while True:
            scrobble_item = self.scrobble_queue.get()
            self.scrobble(*scrobble_item)
            self.scrobble_queue.task_done()

    def scrobble(self, verb, data):
        if trakt.scrobble(verb, **data):
            logger.info(f'Scrobble {verb} successful.')
            if verb != 'pause':
                notify(f"Scrobble {verb} successful for "
                       f"{data['media_info']['title']}.")
            if self.watched_cache:
                self.clear_watched_cache()
        elif verb == 'stop' and data['progress'] > 80:
            logger.warning('Scrobble unsuccessful. Will try again later.')
            self.watched_cache.append(data)
            write_json(self.watched_cache, WATCHED_CACHE_PATH)
        else:
            logger.warning('Scrobble unsuccessful.')

    def clear_watched_cache(self):
        if getattr(self, 'watched_cache_timer', False):
            self.watched_cache_timer.cancel()
        successful = []
        for item in self.watched_cache:
            logger.debug(f'Adding item to history {item}')
            if trakt.add_to_history(**item):
                logger.info('Successfully added media to history.')
                successful.append(item)
        for item in successful:
            self.watched_cache.remove(item)
        write_json(self.watched_cache, WATCHED_CACHE_PATH)
        self.watched_cache_timer = Timer(self.watched_cache_clean_interval,
                                         self.clear_watched_cache)
        self.watched_cache_timer.name = 'watched_cache_cleaner'
        self.watched_cache_timer.start()
