import requests
import logging
from urllib.parse import unquote
from utils import config
from players.player import Player


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


class VLCInfo(Player):
    name = 'vlc'
    BASE_URL = "http://{ip}:{port}".format(**config['players']['vlc'])

    def __init__(self):
        self.is_running = False
        self.status_data = None
        self.playlist_data = None
        self.status_url = self.BASE_URL + '/requests/status.json'
        self.playlist_url = self.BASE_URL + '/requests/playlist.json'
        self.sess = requests.Session()
        self.sess.auth = ('', config['players']['vlc']['password'])

    def check_running(self):
        try:
            self.sess.head(self.status_url)
        except requests.ConnectionError:
            logger.info('Unable to connect to VLC. ' +
                        'Ensure that the web interface is running.')
            self.is_running = False
        else:
            self.is_running = True

    def update_status(self):
        self.check_running()
        if not self.is_running:
            return

        self.status_data = self.sess.get(self.status_url).json()
        self.playlist_data = self.sess.get(self.playlist_url).json()

    @property
    def state(self):
        if self.is_running and self.status_data:
            states = ['stopped', 'paused', 'playing']
            return states.index(self.status_data['state'])
        else:
            return 0

    @property
    def position(self):
        return self.status_data['time'] if self.state else 0

    @property
    def duration(self):
        return self.status_data['length'] if self.state else 0

    @property
    def file_path(self):
        if not self.state:
            return None
        file_data = search_dict_for_current(self.playlist_data)
        file_url = file_data['uri']
        if not file_url.startswith('file://'):
            return None
        return unquote(file_url[file_url.find('://') + 3:])


if __name__ == '__main__':
    vlc = VLCInfo()
    vlc.update_status()
    print(vlc.file_path)
