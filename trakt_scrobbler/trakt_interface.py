import time
import sys
import webbrowser
from datetime import datetime as dt, timedelta as td
from trakt_scrobbler import logger, trakt_key_holder
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.utils import safe_request, read_json, write_json

API_URL = "https://api.trakt.tv"
TRAKT_CACHE_PATH = DATA_DIR / 'trakt_cache.json'
trakt_cache = {}


class TraktAuth:
    TRAKT_TOKEN_PATH = DATA_DIR / 'trakt_token.json'
    TOKEN_EXPIRY_BUFFER = td(days=1)
    _CODE_FETCH_FAILS_LIMIT = 3
    _REFRESH_RETRIES_LIMIT = 3

    def __init__(self):
        self.CLIENT_ID = trakt_key_holder.get_id()
        self.CLIENT_SECRET = trakt_key_holder.get_secret()
        self._token_data = {}
        self._code_fetch_fails = 0
        self._refresh_retries = 0

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "trakt-api-key": self.CLIENT_ID,
            "trakt-api-version": "2",
            "Authorization": "Bearer {}".format(self.get_access_token())
        }

    def get_access_token(self):
        if not self.token_data:
            logger.info("Access token not found. Initiating device authentication.")
            self.device_auth()
        elif self.is_token_expired():
            logger.info("Trakt access token expired. Refreshing.")
            notify("Trakt access token expired. Refreshing.")
            self.refresh_token()
        if not self.token_data or self.is_token_expired():
            # either device_auth or refresh_token failed to get token
            logger.critical("Unable to get access token.")
            notify("Failed to authorize application with Trakt. "
                   "Run 'trakts auth' manually to retry.", stdout=True)
        else:
            return self.token_data['access_token']

    @property
    def token_data(self):
        if not self._token_data:
            self._token_data = read_json(self.TRAKT_TOKEN_PATH)
        return self._token_data

    @token_data.setter
    def token_data(self, value):
        if value is None:
            return
        self._token_data = value
        write_json(self._token_data, self.TRAKT_TOKEN_PATH)

    def get_device_code(self):
        code_request_params = {
            "url": API_URL + "/oauth/device/code",
            "headers": {"Content-Type": "application/json"},
            "json": {"client_id": self.CLIENT_ID}
        }
        code_resp = safe_request('post', code_request_params)
        return code_resp.json() if code_resp else None

    def get_device_token(self, device_code):
        token_request_params = {
            "url": API_URL + "/oauth/device/token",
            "headers": {"Content-Type": "application/json"},
            "json": {
                "code": device_code,
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET
            }
        }
        token_resp = safe_request('post', token_request_params)
        if token_resp is None:
            self._code_fetch_fails += 1
            if self._code_fetch_fails == self._CODE_FETCH_FAILS_LIMIT:
                logger.critical("Unable to get response from trakt.")
                notify("Unable to get response from trakt.", stdout=True)
                sys.exit(1)
            return
        elif token_resp.status_code == 400:
            self._code_fetch_fails = 0
            return False
        elif token_resp.status_code == 200:
            self.token_data = token_resp.json()
            self._code_fetch_fails = 0
            return True
        else:
            logger.critical("Invalid status code of token response.")
            sys.exit(1)

    def device_auth(self):
        code_data = self.get_device_code()
        if not code_data:
            logger.error("Could not get device code.")
            return

        logger.info(f"Verification URL: {code_data['verification_url']}")
        logger.info(f"User Code: {code_data['user_code']}")
        notify("Open {verification_url} in your browser and enter this code: "
               "{user_code}".format(**code_data), timeout=30, stdout=True)
        webbrowser.open(code_data['verification_url'])

        start = time.time()
        while time.time() - start < code_data['expires_in']:
            if self.get_device_token(code_data['device_code']):
                notify('App authorized successfully.', stdout=True)
                logger.info('App authorized successfully.')
                break
            logger.debug('Waiting for user to authorize the app.')
            time.sleep(int(code_data['interval']))
        else:
            logger.error('Timed out during auth.')

    def refresh_token(self):
        if self._refresh_retries == self._REFRESH_RETRIES_LIMIT:
            self.token_data = {}
            self._refresh_retries = 0

            logger.critical("Too many failed refreshes. Clearing token.")
            notify("Trakt token expired. Couldn't auto-refresh token.", stdout=True)
            self.device_auth()
            return

        exchange_params = {
            "url": API_URL + '/oauth/token',
            "headers": {"Content-Type": "application/json"},
            "json": {
                "refresh_token": self.token_data['refresh_token'],
                "client_id": self.CLIENT_ID,
                "client_secret": self.CLIENT_SECRET,
                "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
                "grant_type": "refresh_token"
            }
        }
        self._refresh_retries += 1
        exchange_resp = safe_request('post', exchange_params)

        if exchange_resp and exchange_resp.status_code == 200:
            self.token_data = exchange_resp.json()
            self._refresh_retries = 0
            logger.info('Refreshed access token.')
        else:
            logger.error("Error refreshing token.")

    def token_expires_at(self) -> dt:
        return dt.fromtimestamp(self.token_data['created_at'] + self.token_data['expires_in'])

    def is_token_expired(self) -> bool:
        return self.token_expires_at() - dt.now() < self.TOKEN_EXPIRY_BUFFER

    def clear_token(self):
        self.token_data = {}


trakt_auth = TraktAuth()


def search(query, types=None, year=None, extended=False):
    if not types:
        types = ['movie', 'show', 'episode']
    search_params = {
        "url": API_URL + '/search/' + ",".join(types),
        "params": {'query': query, 'extended': extended,
                   'field': 'title', 'years': year},
        "headers": trakt_auth.headers
    }
    r = safe_request('get', search_params)
    return r.json() if r else None


def get_trakt_id(title, item_type, year=None):
    required_type = 'show' if item_type == 'episode' else 'movie'

    global trakt_cache
    if not trakt_cache:
        trakt_cache = read_json(TRAKT_CACHE_PATH) or {'movie': {}, 'show': {}}

    trakt_id = trakt_cache[required_type].get(title)
    if trakt_id:
        return trakt_id

    logger.debug(f'Searching trakt: Title: "{title}", Year: {year}')
    results = search(title, [required_type], year)
    if results is None:  # Connection error
        return 0  # Dont store in cache
    elif results == [] or results[0]['score'] < 5:  # Weak or no match
        msg = f'Trakt search yielded no results for the {required_type}, {title}'
        msg += f", Year: {year}" * bool(year)
        logger.warning(msg)
        notify(msg)
        trakt_id = -1
    else:
        trakt_id = results[0][required_type]['ids']['trakt']

    trakt_cache[required_type][title] = trakt_id
    logger.debug(f'Trakt ID: {trakt_id}')
    write_json(trakt_cache, TRAKT_CACHE_PATH)
    return trakt_id


def prepare_scrobble_data(title, type, year=None, *args, **kwargs):
    trakt_id = get_trakt_id(title, type, year)
    if trakt_id < 1:
        logger.warning(f"Invalid trakt id for {title}")
        return None
    if type == 'movie':
        return {'movie': {'ids': {'trakt': trakt_id}}}
    elif type == 'episode':
        return {
            'show': {'ids': {'trakt': trakt_id}},
            'episode': {
                'season': kwargs['season'],
                'number': kwargs['episode']
            }
        }


def scrobble(verb, media_info, progress, *args, **kwargs):
    scrobble_data = prepare_scrobble_data(**media_info)
    if not scrobble_data:
        return None
    scrobble_data['progress'] = progress
    scrobble_params = {
        "url": API_URL + '/scrobble/' + verb,
        "headers": trakt_auth.headers,
        "json": scrobble_data
    }
    scrobble_resp = safe_request('post', scrobble_params)
    return scrobble_resp.json() if scrobble_resp else False


def prepare_history_data(watched_at, title, type, year=None, *args, **kwargs):
    trakt_id = get_trakt_id(title, type, year)
    if trakt_id < 1:
        return None
    if type == 'movie':
        return {'movies': [{'ids': {'trakt': trakt_id},
                            'watched_at': watched_at}]}
    else:  # TODO: Group data by show instead of sending episode-wise
        return {'shows': [
            {'ids': {'trakt': trakt_id}, 'seasons': [
                {'number': kwargs['season'], 'episodes': [
                    {'number': kwargs['episode'], 'watched_at': watched_at}]
                 }]
             }]
        }


def add_to_history(media_info, updated_at, *args, **kwargs):
    watched_at = dt.utcfromtimestamp(updated_at).isoformat() + 'Z'
    history = prepare_history_data(watched_at=watched_at, **media_info)
    if not history:
        return
    params = {
        "url": API_URL + '/sync/history',
        "headers": trakt_auth.headers,
        "json": history
    }
    resp = safe_request('post', params)
    if not resp:
        return False
    added = resp.json()['added']
    return (media_info['type'] == 'movie' and added['movies'] > 0) or \
        (media_info['type'] == 'episode' and added['episodes'] > 0)
