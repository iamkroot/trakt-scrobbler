import confuse
import time
from collections import defaultdict
from copy import deepcopy
from threading import Timer
from trakt_scrobbler import config, logger
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.utils import read_json, write_json
from trakt_scrobbler import trakt_interface as trakt


class BacklogCleaner:
    BACKLOG_PATH = DATA_DIR / "watched_backlog.json"
    DEFAULT_BACKLOG = {"movies": {}, "shows": {}}

    def __init__(self, manual=False):
        self.clear_interval = config["backlog"]["clear_interval"].get(confuse.Number())
        self.expiry = config["backlog"]["expiry"].get(confuse.Number())
        self.read_backlog()
        self.timer_enabled = not manual
        if self.timer_enabled:
            self._make_timer()
            self.clear()

    def read_backlog(self):
        backlog = read_json(self.BACKLOG_PATH)
        if not backlog:
            self.backlog = deepcopy(self.DEFAULT_BACKLOG)
        elif isinstance(backlog, dict):
            for show in backlog["shows"].values():
                seasons = defaultdict(dict)
                for season, episodes in show["seasons"].items():
                    # JSON keys have to be strings. Convert the nums to int manually.
                    seasons[int(season)] = {int(num): v for num, v in episodes.items()}
                show["seasons"] = seasons
            self.backlog = backlog
        elif isinstance(backlog, list):  # old backlog style
            # import the items into new style
            self.backlog = deepcopy(self.DEFAULT_BACKLOG)
            for item in backlog:
                self.add(item)

    def save_backlog(self):
        write_json(self.backlog, self.BACKLOG_PATH)

    def remove_expired(self):
        not_expired = []
        for item in self.backlog:
            if item["updated_at"] + self.expiry > time.time():
                not_expired.append(item)
            else:
                logger.warning(f"Item expired: {item}")
        self.backlog = not_expired
        self.save_backlog()

    def _make_timer(self):
        self.timer = Timer(self.clear_interval, self.clear)
        self.timer.name = "backlog_cleaner"
        self.timer.start()

    def add(self, data):
        media_info = data["media_info"]
        title = media_info["title"]
        year = media_info.get("year")
        key = f"{title}{year if year else ''}"

        if media_info["type"] == "episode":
            show = self.backlog["shows"].setdefault(key, {
                "media_info": dict(title=title, year=year, item_type="episode"),
                "seasons": defaultdict(dict)
            })
            season = show["seasons"][media_info["season"]]
            season[media_info["episode"]] = {
                "progress": data["progress"],
                "updated_at": data["updated_at"]
            }
        elif media_info["type"] == "movie":
            self.backlog["movies"][key] = {
                "media_info": dict(title=title, year=year, item_type="movie"),
                "progress": data["progress"],
                "updated_at": data["updated_at"]
            }

        self.save_backlog()

    def clear(self):
        self.remove_expired()
        trakt.bulk_add_to_history(self.backlog)
        self.save_backlog()

        if self.timer_enabled:
            self.timer.cancel()
            self._make_timer()

    def purge(self):
        old_backlog = self.backlog
        self.backlog = deepcopy(self.DEFAULT_BACKLOG)
        self.save_backlog()
        return old_backlog
