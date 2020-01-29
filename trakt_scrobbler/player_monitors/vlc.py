import json
import requests
import logging
import appdirs
from configparser import ConfigParser
from pathlib import Path
from player_monitors.monitor import WebInterfaceMon
from utils import file_uri_to_path

logger = logging.getLogger('trakt_scrobbler')


def search_dict_for_current(dict_):
    """Find a dict which has 'current' key."""
    if isinstance(dict_, list):
        for d in dict_:
            data = search_dict_for_current(d)
            if data:
                return data
    elif 'current' in dict_:
        return dict_
    elif 'children' in dict_:
        return search_dict_for_current(dict_['children'])


class VLCMon(WebInterfaceMon):
    name = 'vlc'
    URL = "http://{ip}:{port}"
    STATES = ['stopped', 'paused', 'playing']

    def __init__(self, scrobble_queue):
        try:
            web_pwd = self.config['password']
            self.URL = self.URL.format(**self.config)
        except KeyError:
            logger.exception('Check config for correct VLC params.')
            return
        super().__init__(scrobble_queue)
        self.sess.auth = ('', web_pwd)
        self.status_url = self.URL + '/requests/status.json'
        self.playlist_url = self.URL + '/requests/playlist.json'

    @classmethod
    def read_player_cfg(cls, auto_keys=None):
        vlcrc_path = Path(appdirs.user_config_dir("vlc", roaming=True)) / "vlcrc"
        vlcrc = ConfigParser(strict=False)
        vlcrc.optionxform = lambda option: option
        if not vlcrc.read(vlcrc_path, encoding="utf-8-sig"):
            raise FileNotFoundError(vlcrc_path)
        return {
            "port": lambda: vlcrc.get("core", "http-port", fallback=8080),
            "password": lambda: vlcrc.get("lua", "http-password")
        }

    def update_status(self):
        try:
            status_data = self.sess.get(self.status_url).json()
        except json.JSONDecodeError:
            raise requests.ConnectionError
        if not status_data['length']:
            self.status = {}
            return
        self.status['duration'] = status_data['length']
        self.status['position'] = status_data['time']
        self.status['state'] = self.STATES.index(status_data['state'])
        self.status['filepath'] = self._get_filepath()

    def _get_filepath(self):
        playlist_data = self.sess.get(self.playlist_url).json()
        file_data = search_dict_for_current(playlist_data)
        return file_uri_to_path(file_data['uri'])
