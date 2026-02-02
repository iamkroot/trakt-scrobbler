import os
import time
import webbrowser
from json.decoder import JSONDecodeError
import confuse
from requests import HTTPError
from trakt_scrobbler import logger
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.file_info import cleanup_guess
from trakt_scrobbler.mediainfo_remap import apply_remap_rules
from trakt_scrobbler.player_monitors.monitor import WebInterfaceMon
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.utils import read_json, safe_request


class PlexToken:
    """A simple wrapper for plex token file

    TODO: Use some form of OS-provided encrypted storage
    """

    PATH = DATA_DIR / "plex_token.txt"
    OLD_PATH = DATA_DIR / "plex_token.json"

    @property
    def data(self):
        try:
            return self.PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            return self.try_migrate_old_file()

    def try_migrate_old_file(self):
        token = read_json(self.OLD_PATH)
        if not token:
            # we really don't have the token
            return None
        # we got the token from old file- move to new
        self.OLD_PATH.unlink()
        self.data = token["token"]
        return token["token"]

    @data.setter
    def data(self, token_data):
        self.PATH.write_text(token_data, encoding="utf-8")

    @data.deleter
    def data(self):
        self.PATH.unlink(missing_ok=True)

    # TODO: Add a is_valid method?

    def __bool__(self):
        return bool(self.data)


token = PlexToken()


class PlexAuth:
    # https://forums.plex.tv/t/authenticating-with-plex/609370
    API_URL = "https://plex.tv/api/v2"
    CLIENT_ID = (
        "com.iamkroot.trakt_scrobbler"  # Reuse from CLI or consistently use this
    )
    PRODUCT = "Trakt Scrobbler"

    def __init__(self):
        self._token_store = token

    def get_pin(self):
        params = {
            "url": f"{self.API_URL}/pins",
            "headers": {"Accept": "application/json"},
            "data": {
                "strong": "true",
                "X-Plex-Product": self.PRODUCT,
                "X-Plex-Client-Identifier": self.CLIENT_ID,
            },
        }
        resp = safe_request("post", params)
        return resp.json() if resp else None

    def device_auth(self):
        pin_data = self.get_pin()
        if not pin_data:
            logger.error("Could not get Plex PIN.")
            return False

        auth_url = (
            f"https://app.plex.tv/auth#?clientID={self.CLIENT_ID}&code={pin_data['code']}"
            f"&context[device][product]={self.PRODUCT}"
        )

        logger.info(f"Verification URL: {auth_url}")
        notify(
            "Opening browser for Plex authentication...", stdout=True, category="plex"
        )

        term_bak = os.environ.pop("TERM", None)
        webbrowser.open(auth_url)
        if term_bak is not None:
            os.environ["TERM"] = term_bak

        # Poll for token
        pin_id = pin_data["id"]
        check_url = f"{self.API_URL}/pins/{pin_id}"

        start_time = time.time()
        poll_interval = 2
        # at max 2 minutes
        expires_in = min(pin_data.get("expiresIn", 120), 120)

        while time.time() - start_time < expires_in:
            params = {
                "url": check_url,
                "headers": {"Accept": "application/json"},
                "params": {"X-Plex-Client-Identifier": self.CLIENT_ID},
            }
            resp = safe_request("get", params)
            if resp and resp.status_code == 200:
                data = resp.json()
                if data.get("authToken"):
                    self._token_store.data = data["authToken"]
                    logger.info("Plex authenticated successfully.")
                    notify(
                        "Plex authenticated successfully.", stdout=True, category="plex"
                    )
                    return True

            time.sleep(poll_interval)

        logger.error("Plex authentication timed out.")
        notify("Plex authentication timed out.", stdout=True, category="plex")
        return False


class PlexMon(WebInterfaceMon):
    name = "plex"
    exclude_import = False
    URL = "{ip_scheme}://{ip}:{port}"
    STATES = {"stopped": 0, "paused": 1, "buffering": 1, "playing": 2}
    CONFIG_TEMPLATE = {
        "ip_scheme": confuse.Choice(["http", "https"], default="http"),
        "ip": confuse.String(default="localhost"),
        "port": confuse.String(default="32400"),
        "poll_interval": confuse.Number(default=10),
        "scrobble_user": confuse.String(default=""),
    }

    def __init__(self, scrobble_queue):
        try:
            self.URL = self.URL.format(**self.config)
        except KeyError:
            logger.exception("Check config for correct Plex params.")
            return
        self.token = token.data
        if not self.token:
            logger.error("Unable to retrieve plex token.")
            notify(
                "Unable to retrieve plex token. Rerun plex auth.", category="exception"
            )
            return
        super().__init__(scrobble_queue)
        self.sess.headers["Accept"] = "application/json"
        self.sess.headers["X-Plex-Token"] = self.token
        self.session_url = self.URL + "/status/sessions"
        self.media_info_cache = {}

    def get_data(self, url):
        resp = self.sess.get(url)
        # TODO: If we get a 401, clear token and restart plex auth flow
        try:
            resp.raise_for_status()
        except HTTPError:
            if resp.status_code == 503 and "Maintenance" in resp.text:
                logger.warning("Plex server unavailable, ignoring")
                return None
            raise

        try:
            data = resp.json()["MediaContainer"]
        except JSONDecodeError:
            logger.exception("Error with decoding")
            logger.debug(resp.text)
            return None

        if data["size"] <= 0:
            return None

        # no user filter
        if not self.config["scrobble_user"] or "User" not in data["Metadata"][0]:
            return data["Metadata"][0]

        for metadata in data["Metadata"]:
            if metadata["User"].get("title") == self.config["scrobble_user"]:
                return metadata

    def _update_status(self):
        status_data = self.get_data(self.session_url)
        if not status_data:
            self.status = {}
            return
        self.status["duration"] = int(status_data["duration"]) / 1000
        self.status["position"] = int(status_data["viewOffset"]) / 1000
        self.status["state"] = self.STATES.get(status_data["Player"]["state"], 0)
        self.status["media_info"] = self.get_media_info(status_data)

    def update_status(self):
        try:
            return self._update_status()
        except KeyError:
            logger.exception("Weird key error in plex. Resetting status.")
            self.status = {}
            return

    def get_media_info(self, status_data):
        media_info = self.media_info_cache.get(status_data["ratingKey"])
        if not media_info:
            if status_data["type"] == "episode":
                # get the show's data
                show_key = status_data["grandparentKey"]
                show_data = self.media_info_cache.get(show_key)
                if not show_data:
                    show_data = self.get_data(self.URL + show_key)
                    self.media_info_cache[show_key] = show_data
            else:
                show_data = None
            media_info = self._get_media_info(status_data, show_data)
            self.media_info_cache[status_data["ratingKey"]] = media_info
        return media_info

    @staticmethod
    def _get_media_info(status_data, show_data=None):
        if status_data["type"] == "movie":
            info = {
                "type": "movie",
                "title": status_data["title"],
                "year": status_data.get("year"),
            }
        elif status_data["type"] == "episode":
            info = {
                "type": "episode",
                "title": status_data["grandparentTitle"],
                "season": status_data["parentIndex"],
                "episode": status_data["index"],
                "year": show_data and show_data.get("year"),
            }
        else:
            logger.warning(f"Unknown media type {status_data['type']}")
            return None

        if info["year"] is not None:
            info["year"] = year = int(info["year"])
            # if year is at the end of the title, like "The Boys (2019)", remove it
            # otherwise it might not show up on Trakt search
            suffix = f" ({year})"
            if info["title"].endswith(suffix):
                info["title"] = info["title"].replace(suffix, "")
        guess = cleanup_guess(info)
        return apply_remap_rules(None, guess) if guess else guess
