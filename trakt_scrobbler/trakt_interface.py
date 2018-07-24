import time
import logging
import requests
from json.decoder import JSONDecodeError
from utils import config, save_config
import trakt_key_holder

logger = logging.getLogger('trakt_scrobbler')

CLIENT_ID = trakt_key_holder.get_id()
CLIENT_SECRET = trakt_key_holder.get_secret()

API_URL = "https://api.trakt.tv"


def safe_request(verb, params):
    """ConnectionError handling for requests methods."""
    try:
        resp = requests.request(verb, **params)
    except requests.exceptions.ConnectionError:
        logger.error('Failed to connect.')
        logger.debug(verb + str(params))
        return None
    else:
        return resp


class TraktAuth:

    def __init__(self):
        self._read_config()
        if not self.access_token:
            logger.info("Access token not found in config. " +
                        "Initiating device authentication.")
            self.device_auth()
        if self._config['expires_at'] - time.time() < 3600:
            logger.info("Access token about to expire. Updating.")
            self.exchange_refresh_access_tokens()

    def _read_config(self):
        self._config = config['trakt']
        self.access_token = self._config.get('access_token')

    def _save_config(self):
        config['trakt'] = self._config
        save_config(config)

    def get_device_code(self):
        code_request_params = {
            "url": API_URL + "/oauth/device/code",
            "headers": {"Content-Type": "application/json"},
            "json": {"client_id": CLIENT_ID}
        }
        code_resp = safe_request('post', code_request_params)
        return code_resp.json() if code_resp else None

    def get_device_token(self, device_code):
        token_request_params = {
            "url": API_URL + "/oauth/device/token",
            "headers": {"Content-Type": "application/json"},
            "json": {
                "code": device_code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            }
        }
        token_resp = safe_request('post', token_request_params)
        if not token_resp:
            return
        elif token_resp.status_code == 400:
            logger.info('Waiting for user to authorize the app.')
        elif token_resp.status_code == 200:
            return token_resp.json()
        else:
            logger.error('Invalid status code of token response.')
            exit(0)

    def device_auth(self):
        code_data = self.get_device_code()
        if not code_data:
            logger.warning('Failed device auth.')
            return
        logger.debug(f"User Code: {code_data['user_code']}")
        logger.debug(f"Verification URL: {code_data['verification_url']}")
        print("User Code:", code_data['user_code'])
        print(f"Go to {code_data['verification_url']} and enter this code.")
        start = time.time()
        while time.time() - start < code_data['expires_in']:
            try:
                token_data = self.get_device_token(code_data['device_code'])
            except JSONDecodeError:
                time.sleep(int(code_data['interval']))
                continue
            else:
                print('Successful.')
                logger.info('Device auth successful.')
                break
        else:
            logger.error('Timed out during auth.')
            exit(0)
        self.read_token_data(token_data)

    def read_token_data(self, data):
        self.access_token = data['access_token']
        self._config['access_token'] = self.access_token
        self._config['refresh_token'] = data['refresh_token']
        self._config['expires_at'] = data['created_at'] + data['expires_in']
        self._save_config()

    def exchange_refresh_access_tokens(self):
        logger.debug(f"Refresh token: {self._config['refresh_token']}")
        exchange_params = {
            "url": API_URL + '/oauth/token',
            "headers": {"Content-Type": "application/json"},
            "json": {
                "refresh_token": self._config['refresh_token'],
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "refresh_token"
            }
        }
        exchange_resp = safe_request('post', exchange_params)
        if exchange_resp and exchange_resp.status_code == 200:
            logger.info('Refreshed access token.')
            self.read_token_data(exchange_resp.json())
        else:
            logger.info("Error refreshing token.")


class TraktAPI:
    """Handles all scrobbling with Trakt.tv API."""

    def __init__(self):
        self.access_token = TraktAuth().access_token
        self.headers = {
            "Content-Type": "application/json",
            "trakt-api-key": CLIENT_ID,
            "trakt-api-version": "2",
            "Authorization": f"Bearer {self.access_token}"
        }

    def scrobble(self, verb, data):
        scrobble_params = {
            "url": API_URL + '/scrobble/' + verb,
            "headers": self.headers,
            "json": data
        }
        scrobble_resp = safe_request('post', scrobble_params)
        return scrobble_resp.json() if scrobble_resp else None

    def search(self, query, types=None, extended=False):
        if not types:
            types = ['movie', 'show', 'episode']
        search_params = {
            "url": API_URL + '/search/' + ",".join(types),
            "params": {'query': query, 'extended': extended, 'field': 'title'},
            "headers": self.headers
        }
        r = safe_request('get', search_params)
        return r.json() if r else None
