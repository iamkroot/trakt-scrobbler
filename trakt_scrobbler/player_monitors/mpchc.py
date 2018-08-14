import re
import logging
from player_monitors.monitor import WebInterfaceMon
from utils import config

logger = logging.getLogger('trakt_scrobbler')


class MPCHCMon(WebInterfaceMon):
    name = 'mpchc'
    URL = "http://{ip}:{port}/variables.html"

    def __init__(self, scrobble_queue):
        try:
            self.URL = self.URL.format(**config['players']['mpchc'])
        except KeyError:
            logger.error('Check config for correct MPCHC params.')
            return
        super().__init__(scrobble_queue)

    def get_vars(self):
        response = self.sess.get(self.URL)
        pattern = re.compile(r'\<p id=\"([a-z]+)\"\>(.*?)\<', re.MULTILINE)
        matches = pattern.findall(response.text)
        return {var[0]: var[1] for var in matches}

    def update_status(self):
        variables = self.get_vars()
        if variables['duration'] == '0':
            self.reset_status()
            return
        self.status['state'] = int(variables['state'])
        for key in ('position', 'duration'):
            self.status[key] = int(variables[key]) / 1000
        if self.status['position'] == self.status['duration']:
            self.status['state'] = 0
        self.status['filepath'] = variables['filepath']
