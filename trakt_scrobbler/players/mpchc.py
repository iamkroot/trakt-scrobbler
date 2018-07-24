import re
import requests
import logging
from utils import config
from players.player import Player

logger = logging.getLogger('trakt_scrobbler')


class MPCHCInfo(Player):
    """MPCHC Status."""
    name = 'mpchc'

    def __init__(self):
        self._variables = None
        self.is_running = False
        self.URL = "http://{ip}:{port}/variables.html".format(
            **config['players']['mpchc'])

    def check_running(self):
        try:
            requests.head(self.URL)
        except requests.ConnectionError:
            logger.info('Unable to connect to MPCHC. ' +
                        'Ensure that the web interface is running.')
            self.is_running = False
        else:
            self.is_running = True

    def update_status(self):
        self.check_running()
        if not self.is_running:
            return
        response = requests.get(self.URL)
        pattern = re.compile(r'\<p id=\"([a-z]+)\"\>(.*?)\<', re.MULTILINE)
        matches = pattern.findall(response.text)
        self._variables = {var[0]: var[1] for var in matches}

    @property
    def state(self):
        if self.is_running and self._variables:
            return int(self._variables['state'])
        else:
            return 0

    @property
    def position(self):
        return int(self._variables['position']) if self.state else 0

    @property
    def duration(self):
        return int(self._variables['duration']) if self.state else 0

    @property
    def file_path(self):
        return self._variables['filepath'] if self._variables else None


if __name__ == '__main__':
    pass
