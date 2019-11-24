import logging
from app_dirs import DATA_DIR
from player_monitors.monitor import WebInterfaceMon
from utils import config, read_json, write_json, safe_request

logger = logging.getLogger('trakt_scrobbler')
PLEX_TOKEN_PATH = DATA_DIR / "plex_token.json"


def plex_token_auth(login, password):
    auth_params = {
        "url": "https://plex.tv/users/sign_in.json",
        "data": {
            "user[login]": login,
            "user[password]": password
        },
        "headers": {
            "X-Plex-Client-Identifier": "com.iamkroot.trakt_scrobbler",
            "X-Plex-Product": "Trakt Scrobbler",
            "Accept": "application/json"
        }
    }
    resp = safe_request("post", auth_params)
    if not resp:
        return None
    return resp.json()["user"]["authToken"]


def get_token(**kwargs):
    token = kwargs.get("token") or read_json(PLEX_TOKEN_PATH).get("token")
    if token:
        return token
    token = plex_token_auth(kwargs["login"], kwargs["password"])
    write_json({"token": token}, PLEX_TOKEN_PATH)
    return token


class PlexMon(WebInterfaceMon):
    name = "plex"
    exclude_import = False
    URL = "http://{ip}:{port}"
    STATES = {"stopped": 0, "paused": 1, "buffering": 1, "playing": 2}

    def __init__(self, scrobble_queue):
        try:
            plex_conf = config["players"]["plex"]
            self.token = get_token(**plex_conf)
            self.URL = self.URL.format(**plex_conf)
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
        self.metadata_url = self.URL + "/library/metadata/{}"

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
        # TODO: Use plex metadata to directly get media info instead of filepath
        self.status["filepath"] = self._get_filepath(status_data["ratingKey"])

    def _get_filepath(self, key):
        metadata = self.get_data(self.metadata_url.format(key))
        try:
            return metadata["Media"][0]["Part"][0]["file"]
        except (KeyError, AttributeError):
            logger.exception("Unable to fetch filepath.")
            logger.debug(metadata)
