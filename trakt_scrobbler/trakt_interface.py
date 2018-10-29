import logging
import time
import sys
import trakt_key_holder
from datetime import datetime as dt
from functools import lru_cache
from utils import DATA_DIR, safe_request, read_json, write_json

logger = logging.getLogger('trakt_scrobbler')

CLIENT_ID = trakt_key_holder.get_id()
CLIENT_SECRET = trakt_key_holder.get_secret()
API_URL = "https://api.trakt.tv"
TRAKT_CACHE_PATH = DATA_DIR / 'trakt_cache.json'
TRAKT_TOKEN_PATH = DATA_DIR / 'trakt_token.json'
trakt_cache = read_json(TRAKT_CACHE_PATH) or {'movie': {}, 'show': {}}


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
        sys.exit(1)


def device_auth():
    code_data = get_device_code()
    if not code_data:
        logger.error('Failed device auth.')
        sys.exit(1)

    logger.info(f"Verification URL: {code_data['verification_url']}")
    logger.info(f"User Code: {code_data['user_code']}")
    print(f"Go to {code_data['verification_url']} and enter this code.")
    print("User Code:", code_data['user_code'])

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
        sys.exit(1)
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
    token_data = read_json(TRAKT_TOKEN_PATH)
    if not token_data:
        logger.info("Access token not found in config. " +
                    "Initiating device authentication.")
        token_data = device_auth()
    elif token_data['created_at'] + token_data['expires_in'] - \
            time.time() < 86400:
        logger.info("Access token about to expire. Refreshing.")
        token_data = refresh_token(token_data)
    write_json(token_data, TRAKT_TOKEN_PATH)
    return token_data['access_token']


def get_headers():
    return {
        "Content-Type": "application/json",
        "trakt-api-key": CLIENT_ID,
        "trakt-api-version": "2",
        "Authorization": "Bearer {}".format(get_access_token())
    }


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


@lru_cache(maxsize=None)
def get_trakt_id(title, item_type):
    required_type = 'show' if item_type == 'episode' else 'movie'

    logger.debug('Searching cache.')
    trakt_id = trakt_cache[required_type].get(title)
    if trakt_id:
        return trakt_id

    logger.debug('Searching trakt.')
    results = search(title, [required_type])
    if results is None:  # Connection error
        return 0  # Dont store in cache
    elif results == [] or results[0]['score'] < 0.1:  # Weak or no match
        logger.warning('Trakt search yielded no results.')
        trakt_id = -1
    else:
        trakt_id = results[0][required_type]['ids']['trakt']

    trakt_cache[required_type][title] = trakt_id
    logger.debug(f'Trakt ID: {trakt_id}')
    write_json(trakt_cache, TRAKT_CACHE_PATH)
    return trakt_id


def prepare_scrobble_data(title, type, *args, **kwargs):
    trakt_id = get_trakt_id(title, type)
    if trakt_id < 1:
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
        "headers": get_headers(),
        "json": scrobble_data
    }
    scrobble_resp = safe_request('post', scrobble_params)
    return scrobble_resp.json() if scrobble_resp else None


def prepare_history_data(watched_at, title, type, *args, **kwargs):
    trakt_id = get_trakt_id(title, type)
    if trakt_id < 1:
        return None
    if type == 'movie':
        return {'movies': [{'ids': {'trakt': trakt_id},
                            'watched_at': watched_at}]}
    else:
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
        "headers": get_headers(),
        "json": history
    }
    resp = safe_request('post', params)
    if resp:
        added = resp.json()['added']
        if (media_info['type'] == 'movie' and added['movies'] > 0) or \
           (media_info['type'] == 'episode' and added['episodes'] > 0):
            return True
