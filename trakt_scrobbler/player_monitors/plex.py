from getpass import getpass

import confuse
from trakt_scrobbler import logger
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.player_monitors.monitor import WebInterfaceMon
from trakt_scrobbler.utils import read_json, safe_request, write_json

PLEX_TOKEN_PATH = DATA_DIR / "plex_token.json"
token_data = {}


def plex_token_auth(login, password):
    auth_params = {
        "url": "https://plex.tv/users/sign_in.json",
        "data": {"user[login]": login, "user[password]": password},
        "headers": {
            "X-Plex-Client-Identifier": "com.iamkroot.trakt_scrobbler",
            "X-Plex-Product": "Trakt Scrobbler",
            "Accept": "application/json",
        },
    }
    return safe_request("post", auth_params)


def get_token():
    global token_data
    token_data = read_json(PLEX_TOKEN_PATH) or {}

    if not token_data:
        logger.info("Retrieving plex token")
        login = input("Plex login ID: ")
        pwd = getpass()
        resp = plex_token_auth(login, pwd)
        if resp.ok:
            token_data = {"token": resp.json()["user"]["authToken"]}
            write_json(token_data, PLEX_TOKEN_PATH)
            logger.info(f"Saved plex token to {PLEX_TOKEN_PATH}")
        elif resp is not None:
            print(resp.json().get("error", resp.text))
            return None
        else:
            logger.error(
                "Unable to get access token. "
                f"Try deleting {PLEX_TOKEN_PATH!s} and retry."
            )
            return None
    return token_data['token']


class PlexMon(WebInterfaceMon):
    name = "plex"
    exclude_import = False
    URL = "http://{ip}:{port}"
    STATES = {"stopped": 0, "paused": 1, "buffering": 1, "playing": 2}
    CONFIG_TEMPLATE = {
        "ip": confuse.String(default="localhost"),
        "port": confuse.String(default="32400"),
        "poll_interval": confuse.Number(default=10),
    }

    def __init__(self, scrobble_queue):
        try:
            self.token = get_token()
            self.URL = self.URL.format(**self.config)
        except KeyError:
            logger.exception("Check config for correct Plex params.")
            return
        if not self.token:
            logger.error("Unable to retrieve plex token.")
            return
        super().__init__(scrobble_queue)
        self.sess.headers["Accept"] = "application/json"
        self.sess.headers["X-Plex-Token"] = self.token
        self.session_url = self.URL + "/status/sessions"
        self.media_info_cache = {}

    def get_data(self, url):
        data = self.sess.get(url).json()["MediaContainer"]
        if data["size"] > 0:
            return data["Metadata"][0]

    def update_status(self):
        status_data = self.get_data(self.session_url)
        if not status_data:
            self.status = {}
            return
        self.status["duration"] = int(status_data["duration"]) / 1000
        self.status["position"] = int(status_data["viewOffset"]) / 1000
        self.status["state"] = self.STATES.get(status_data["Player"]["state"], 0)
        self.status["media_info"] = self.get_media_info(status_data)

    def get_media_info(self, status_data):
        media_info = self.media_info_cache.get(status_data["ratingKey"])
        if not media_info:
            media_info = self._get_media_info(status_data)
            self.media_info_cache[status_data["ratingKey"]] = media_info
        return media_info

    @staticmethod
    def _get_media_info(status_data):
        if status_data["type"] == "movie":
            return {"type": "movie", "title": status_data["title"]}
        elif status_data["type"] == "episode":
            return {
                "type": "episode",
                "title": status_data["grandparentTitle"],
                "season": status_data["parentIndex"],
                "episode": status_data["index"],
            }
