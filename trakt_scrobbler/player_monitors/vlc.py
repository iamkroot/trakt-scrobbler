import logging
from player_monitors.monitor import WebInterfaceMon
from utils import config, file_uri_to_path

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

    def update_status(self):
        status_data = self.sess.get(self.status_url).json()
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
