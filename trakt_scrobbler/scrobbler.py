from threading import Thread
from trakt_scrobbler import logger
from trakt_scrobbler import trakt_interface as trakt
from trakt_scrobbler.notifier import notify


class Scrobbler(Thread):
    """Scrobbles the data from queue to Trakt."""

    def __init__(self, scrobble_queue, backlog_cleaner):
        super().__init__(name='scrobbler')
        logger.info('Started scrobbler thread.')
        self.scrobble_queue = scrobble_queue
        self.backlog_cleaner = backlog_cleaner
        self.prev_scrobble = None

    def run(self):
        while True:
            scrobble_item = self.scrobble_queue.get()
            self.scrobble(*scrobble_item)
            self.scrobble_queue.task_done()

    def is_resume(self, verb, data):
        if not self.prev_scrobble or verb != "start":
            return False
        prev_verb, prev_data = self.prev_scrobble
        return prev_verb == "pause" and prev_data['media_info'] == data['media_info']

    def scrobble(self, verb, data):
        logger.debug(f"Scrobbling {verb} at {data['progress']:.2f}% for "
                     f"{data['media_info']['title']}")
        resp = trakt.scrobble(verb, **data)
        if resp:
            if 'movie' in resp:
                name = resp['movie']['title']
            else:
                name = (resp['show']['title'] +
                        " S{season:02}E{number:02}".format(**resp['episode']))
            category = 'resume' if self.is_resume(verb, data) else verb
            msg = f"Scrobble {category} successful for {name}"
            logger.info(msg)
            notify(msg, category=f"scrobble.{category}")
            self.backlog_cleaner.clear()
        elif resp is False and verb == 'stop' and data['progress'] > 80:
            logger.warning('Scrobble unsuccessful. Will try again later.')
            self.backlog_cleaner.add(data)
        else:
            logger.warning('Scrobble unsuccessful.')
        self.prev_scrobble = (verb, data)
