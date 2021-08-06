import os
import sys
import time
import webbrowser
from datetime import datetime as dt, timedelta as td
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler import logger, trakt_key_holder
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.utils import read_json, write_json, safe_request

API_URL = "https://api.trakt.tv"


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
            notify("Trakt access token expired. Refreshing.", category="trakt")
            self.refresh_token()
        if not self.token_data or self.is_token_expired():
            # either device_auth or refresh_token failed to get token
            logger.critical("Unable to get access token.")
            notify("Failed to authorize application with Trakt. "
                   "Run 'trakts auth' manually to retry.",
                   stdout=True, category="trakt")
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
                notify("Unable to get response from trakt.",
                       stdout=True, category="trakt")
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
        notify(
            "Open {verification_url} in your browser and enter this code: "
            "{user_code}".format(**code_data), timeout=30, stdout=True,
            category="trakt")

        # automatically open the url in the default browser
        # but we don't want to use terminal-based browsers - most likely not
        # what the user wants
        term_bak = os.environ.pop("TERM", None)
        webbrowser.open(code_data['verification_url'])
        if term_bak is not None:
            os.environ["TERM"] = term_bak

        start = time.time()
        while time.time() - start < code_data['expires_in']:
            if self.get_device_token(code_data['device_code']):
                notify('App authorized successfully.',
                       stdout=True, category="trakt")
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
