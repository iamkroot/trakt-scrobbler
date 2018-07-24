import time
import logging
from threading import Thread
from utils import config
from trakt_interface import TraktAPI

logger = logging.getLogger('trakt_scrobbler')


def update_percent(item, new_time):
    """Calculate the new progress of media."""
    item['position'] += round(new_time - item['time'], 2)
    try:
        progress = round(item['position'] / item['duration'] * 100, 2)
    except ZeroDivisionError:
        progress = 0
    item['progress'] = progress if progress <= 100 else 100


class Scrobbler(Thread):
    """Scrobbles the data from queue to Trakt."""

    def __init__(self, scrobble_queue, scrobble_interval=60):
        super().__init__(name='scrobbler')
        self.scrobble_queue = scrobble_queue
        self.scrobble_interval = scrobble_interval
        self.players = config['players']['priorities']
        self.player_inds = {p: i for i, p in enumerate(self.players)}
        self.trakt = TraktAPI()
        self._cache = []
        self.final_actions = []

    def run(self):
        while True:
            if self.scrobble_queue.qsize() == 0:
                time.sleep(self.scrobble_interval)
                continue
            scrobble_data = self.scrobble_queue.get()
            self._cache.append(scrobble_data)
            if self.scrobble_queue.qsize() == 0:
                self.scrobble()
            self.scrobble_queue.task_done()

    def _get_last_states(self):
        """Extract the last known status of each file."""
        unique_media = []
        last_states = []
        self._cache.reverse()
        for item in self._cache:
            if item.get('file_info') and item['file_info'] not in unique_media:
                last_states.append(item)
                unique_media.append(item['file_info'])
        last_states.reverse()  # most recent entries will be at the end
        return last_states

    def _group_cache_by_player_name(self):
        """Group cache by players."""
        grouped = {}
        for player in self.players:
            grouped[player] = list(filter(
                lambda item: item['player'] == player, self._cache))
        return grouped

    def determine_actions(self):
        """Parse the cache and determine the final scrobble actions.

        It finds the last known status of each file in the cache. If the state
        is paused or stopped, that action in created. Otherwise, if the state
        is playing, two cases are possible. Either it is the currently playing
        file, or another entry was added to cache without stopping/pausing that
        file. We get the index of the item in the cache, corresponding to the
        player it came from. If index is not 0, we have to send a 'stop'
        scrobble action for the item, otherwise, it will be added to shortlist
        for playing status. It is possible that multiple players have files
        playing currently. The file of player with highest priority will be
        scrobbled as 'play' and others will be scrobbled 'stop'.
        """
        last_states = self._get_last_states()
        cache_by_player = self._group_cache_by_player_name()
        self._cache.reverse()
        playing_shortlist = []  # all items with 'playing' as their last status

        # player with most priority, will be overriden later
        best_player = self.players[-1]

        for item in last_states:
            if item['state'] < 2:  # if item is stopped/paused
                update_percent(item, item['time'])
                self.create_action(['stop', 'pause'][item['state']], item)
                continue

            player = item['player']
            filtered_cache = cache_by_player[player]
            ind = filtered_cache.index(item)

            # there is another item in the player cache after the current item
            if ind > 0:  # most recent entries will be at beginning
                # update the progress according to the next item's time
                update_percent(item, filtered_cache[ind - 1]['time'])
                self.create_action('stop', item)
            # this is the last known item with playing status in player
            elif ind == 0:
                update_percent(item, time.time())
                if item['progress'] == 100:
                    self.create_action('stop', item)
                    continue
                playing_shortlist.append(item)
                if self.player_inds[player] < self.player_inds[best_player]:
                    best_player = player  # find player with highest priority

        for item in playing_shortlist:
            if item['player'] == best_player:
                self.create_action('start', item)
            else:
                self.create_action('stop', item)

    def create_action(self, verb, item):
        data = item['file_info'].copy()
        data['progress'] = item['progress']
        self.final_actions.append((verb, data, item))

    def scrobble(self):
        self.determine_actions()
        for verb, data, item in self.final_actions:
            logger.info('Scrobbling ' + verb + str(data))
            if not self.trakt.scrobble(verb, data):
                logger.warning('Invalid response while trying to scrobble.')
                continue
            # clear cache upto current entry
            del self._cache[:self._cache.index(item) + 1]
            if verb == 'start':
                # save the media info for next time the queue is emptied
                self._cache.append(item)
        self.final_actions.clear()
