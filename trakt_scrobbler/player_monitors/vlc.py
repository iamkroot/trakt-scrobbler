import logging
from urllib.parse import unquote
from player_monitors.monitor import WebInterfaceMon
from utils import config

logger = logging.getLogger('trakt_scrobbler')


def search_dict_for_current(search_dict):
    if isinstance(search_dict, list):
        for d in search_dict:
            data = search_dict_for_current(d)
            if data:
                return data
    elif 'current' in search_dict:
        return search_dict
    elif 'children' in search_dict:
        return search_dict_for_current(search_dict['children'])


class VLCMon(WebInterfaceMon):
    name = 'vlc'
    URL = "http://{ip}:{port}"

    def __init__(self, scrobble_queue):
        try:
            vlc_conf = config['players']['vlc']
            web_pwd = vlc_conf['password']
            self.URL = self.URL.format(**vlc_conf)
        except KeyError:
            logger.error('Check config for correct VLC params.')
            return
        super().__init__(scrobble_queue)
        self.sess.auth = ('', web_pwd)
        self.status_url = self.URL + '/requests/status.json'
        self.playlist_url = self.URL + '/requests/playlist.json'
        self.states = ['stopped', 'paused', 'playing']

    def update_status(self):
        status_data = self.sess.get(self.status_url).json()
        if not status_data['length']:
            self.reset_status()
            return
        self.status['duration'] = status_data['length']
        self.status['position'] = status_data['time']
        self.status['state'] = self.states.index(status_data['state'])
        self.status['filepath'] = self._get_filepath()

    def _get_filepath(self):
        playlist_data = self.sess.get(self.playlist_url).json()
        file_data = search_dict_for_current(playlist_data)
        file_url = file_data['uri']
        if not file_url.startswith('file://'):
            return None
        return unquote(file_url[file_url.find('://') + 3:])
