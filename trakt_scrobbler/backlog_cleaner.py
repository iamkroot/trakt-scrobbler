import confuse
from collections import defaultdict
from copy import deepcopy
from threading import Timer
from trakt_scrobbler import config, logger
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.utils import read_json, write_json
from trakt_scrobbler import trakt_interface as trakt


def _read_shows(shows: dict):
    for show in shows.values():
        seasons = defaultdict(dict)
        for season, episodes in show["seasons"].items():
            # JSON keys have to be strings. Convert the nums to int manually.
            seasons[int(season)] = {int(num): v for num, v in episodes.items()}
        show["seasons"] = seasons


class BacklogCleaner:
    BACKLOG_PATH = DATA_DIR / "watched_backlog.json"
    DEFAULT_BACKLOG = {"movies": {}, "shows": {}}

    def __init__(self, manual=False):
        self.clear_interval = config["backlog"]["clear_interval"].get(confuse.Number())
        self.unknown_items = UnknownItems()
        self.timer_enabled = not manual
        if self.timer_enabled:
            self._make_timer()
            self.clear()

    @property
    def backlog(self):
        return self.read_backlog()

    @backlog.setter
    def backlog(self, value):
        self._backlog = value
        self.save_backlog()

    def read_backlog(self):
        backlog = read_json(self.BACKLOG_PATH)
        if not backlog:
            self._backlog = deepcopy(self.DEFAULT_BACKLOG)
        elif isinstance(backlog, dict):
            _read_shows(backlog["shows"])
            self._backlog = backlog
        elif isinstance(backlog, list):  # old backlog style
            # import the items into new style
            self._backlog = deepcopy(self.DEFAULT_BACKLOG)
            for item in backlog:
                self.add(item)
        return self._backlog

    def save_backlog(self):
        write_json(self._backlog, self.BACKLOG_PATH)

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

    def mark_invalid(self, category, key):
        item = self.backlog[category].pop(key)
        self.unknown_items.add(category, key, item)

    def clear(self):
        result = trakt.bulk_add_to_history(self.backlog)
        added, invalid = {}, {}
        if result is not False:
            invalid, resp = result
            for category, keys in invalid.items():
                for key in keys:
                    self.mark_invalid(category, key)
            added = resp.get("added", {})
            if any(added.values()):
                logger.info(f"Added to history: {added}")
            if any(resp.get("not_found", {}).values()):
                logger.warning(f"Not found on trakt: {resp['not_found']}")
            self.backlog = deepcopy(self.DEFAULT_BACKLOG)

        if self.timer_enabled:
            self.timer.cancel()
            self._make_timer()

        return result is not False, added, invalid

    def purge(self):
        old_backlog = self.backlog
        self.backlog = deepcopy(self.DEFAULT_BACKLOG)
        return old_backlog


class UnknownItems:
    """Represents the watched movies or shows for which we couldn't find any TraktID"""
    UNKNOWN_ITEMS_PATH = DATA_DIR / "unknown_items.json"

    @property
    def unknown_items(self):
        return self.read()

    @unknown_items.setter
    def unknown_items(self, value):
        self._unknown_items = value
        self.save()

    def read(self):
        self._unknown_items = read_json(self.UNKNOWN_ITEMS_PATH) or \
            deepcopy(BacklogCleaner.DEFAULT_BACKLOG)
        _read_shows(self._unknown_items["shows"])
        return self._unknown_items

    def save(self):
        write_json(self._unknown_items, self.UNKNOWN_ITEMS_PATH)

    def add(self, category, key, item):
        logger.info(f"Adding to unknown {category}: {item}")
        if category == "movies":
            self.unknown_items["movies"][key] = item
        elif category == "shows":
            show = self.unknown_items["shows"].setdefault(key, {
                "media_info": item["media_info"],
                "seasons": defaultdict(dict)
            })
            for season, episodes in item["seasons"].items():
                show["seasons"][season].update(episodes)
        self.save()

    # TODO: Allow the user to manually specify correct TraktIDs
