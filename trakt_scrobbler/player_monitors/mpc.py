import re
import logging
from player_monitors.monitor import WebInterfaceMon

logger = logging.getLogger('trakt_scrobbler')


class MPCMon(WebInterfaceMon):
    exclude_import = True
    URL = "http://{ip}:{port}/variables.html"
    PATTERN = re.compile(r'\<p id=\"([a-z]+)\"\>(.*?)\<', re.MULTILINE)

    def __init__(self, scrobble_queue):
        try:
            self.URL = self.URL.format(**self.config)
        except KeyError:
            logger.exception(f'Check config for correct {self.name} params.')
            return
        super().__init__(scrobble_queue)

    @classmethod
    def read_player_cfg(cls, auto_keys=None):
        import winreg
        subkey = f"Software\\{cls.name.upper()}\\Settings"
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey)
        return {"port": lambda: winreg.QueryValueEx(hkey, "WebServerPort")[0]}

    def get_vars(self):
        response = self.sess.get(self.URL)
        matches = self.PATTERN.findall(response.text)
        return dict(matches)

    def update_status(self):
        variables = self.get_vars()
        if variables['duration'] == '0':
            self.status = {}
            return
        self.status['state'] = int(variables['state'])
        for key in ('position', 'duration'):
            self.status[key] = int(variables[key]) / 1000
        # instead of stopping, mpc pauses the file at the last second
        if variables['positionstring'] == variables['durationstring']:
            self.status['state'] = 0
        self.status['filepath'] = variables['filepath']


class MPCHCMon(MPCMon):
    exclude_import = False
    name = 'mpc-hc'


class MPCBEMon(MPCHCMon):
    exclude_import = False
    name = 'mpc-be'
