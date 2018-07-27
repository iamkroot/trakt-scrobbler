import logging
import time
import trakt_key_holder
from utils import safe_request, read_json, write_json

logger = logging.getLogger('trakt_scrobbler')

CLIENT_ID = trakt_key_holder.get_id()
CLIENT_SECRET = trakt_key_holder.get_secret()
API_URL = "https://api.trakt.tv"


def get_device_code():
    code_request_params = {
        "url": API_URL + "/oauth/device/code",
        "headers": {"Content-Type": "application/json"},
        "json": {"client_id": CLIENT_ID}
    }
    code_resp = safe_request('post', code_request_params)
    return code_resp.json() if code_resp else None


def get_device_token(device_code):
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
        return
    elif token_resp.status_code == 200:
        return token_resp.json()
    else:
        logger.error('Invalid status code of token response.')
        exit(0)


def device_auth():
    code_data = get_device_code()
    if not code_data:
        logger.error('Failed device auth.')
        exit(0)

    logger.debug(f"User Code: {code_data['user_code']}")
    logger.debug(f"Verification URL: {code_data['verification_url']}")
    print("User Code:", code_data['user_code'])
    print(f"Go to {code_data['verification_url']} and enter this code.")

    start = time.time()
    while time.time() - start < code_data['expires_in']:
        token_data = get_device_token(code_data['device_code'])
        if not token_data:
            logger.debug('Waiting for user to authorize app.')
            time.sleep(int(code_data['interval']))
        else:
            print('Successful.')
            logger.info('Device auth successful.')
            break
    else:
        logger.error('Timed out during auth.')
        exit(0)
    token_data['expires_at'] = token_data['created_at'] + token_data['expires_in']
    return token_data


def refresh_token(token_data):
    exchange_params = {
        "url": API_URL + '/oauth/token',
        "headers": {"Content-Type": "application/json"},
        "json": {
            "refresh_token": token_data['refresh_token'],
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "refresh_token"
        }
    }
    exchange_resp = safe_request('post', exchange_params)
    if exchange_resp and exchange_resp.status_code == 200:
        logger.info('Refreshed access token.')
        return exchange_resp.json()
    else:
        logger.info("Error refreshing token.")


def get_access_token():
    token_data = read_json('trakt_token.json')
    if not token_data:
        logger.info("Access token not found in config. " +
                    "Initiating device authentication.")
        token_data = device_auth()
    elif token_data['expires_at'] - time.time() < 86400:
        logger.info("Access token about to expire. Refreshing.")
        token_data = refresh_token(token_data)
    write_json(token_data, 'trakt_token.json')
    return token_data['access_token']


def get_headers():
    return {
        "Content-Type": "application/json",
        "trakt-api-key": CLIENT_ID,
        "trakt-api-version": "2",
        "Authorization": "Bearer {}".format(get_access_token())
    }


def scrobble(verb, data):
    scrobble_params = {
        "url": API_URL + '/scrobble/' + verb,
        "headers": get_headers(),
        "json": data
    }
    scrobble_resp = safe_request('post', scrobble_params)
    return scrobble_resp.json() if scrobble_resp else None


def search(query, types=None, extended=False):
    if not types:
        types = ['movie', 'show', 'episode']
    search_params = {
        "url": API_URL + '/search/' + ",".join(types),
        "params": {'query': query, 'extended': extended, 'field': 'title'},
        "headers": get_headers()
    }
    r = safe_request('get', search_params)
    return r.json() if r else None
