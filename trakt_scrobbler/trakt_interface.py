from datetime import datetime as dt
from http import HTTPStatus
from functools import wraps

import requests
from requests.sessions import merge_setting
from trakt_scrobbler import logger
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.trakt_auth import API_URL, TraktAuth
from trakt_scrobbler.utils import safe_request, read_json, write_json

trakt_auth = TraktAuth()
TRAKT_CACHE_PATH = DATA_DIR / 'trakt_cache.json'
trakt_cache = {}
sess = requests.Session()


def trakt_endpoint(func):
    _AUTH_RETRIES_LIMIT = 3
    _auth_retries = 0

    def handle_params(verb, params):
        nonlocal _auth_retries
        params['headers'] = merge_setting(params.get('headers', {}), trakt_auth.headers)
        params.setdefault('timeout', 30)
        resp = safe_request(verb, params)
        if resp is not None and resp.status_code == HTTPStatus.UNAUTHORIZED:
            if _auth_retries < _AUTH_RETRIES_LIMIT:
                _auth_retries += 1
                logger.info("Forcing trakt authentication")
                trakt_auth.clear_token()
                if not trakt_auth.get_access_token():
                    logger.error("Failed to retrieve trakt token.")
                    return None
                else:
                    return handle_params(verb, params)
            else:
                logger.critical("Failed to retrieve trakt token. Max retries exceeded.")
                raise SystemExit(1)
        else:
            _auth_retries = 0
            return resp

    @wraps(func)
    def wrapped(*args, **kwargs):
        coro = func(*args, **kwargs)
        try:
            verb, params = next(coro)
        except StopIteration as i:
            return i.value
        resp = handle_params(verb, params)
        try:
            coro.send(resp)
        except StopIteration as i:
            return i.value
        else:
            raise Exception("We only support endpoints with single yield")
    return wrapped


@trakt_endpoint
def search(query, types=None, year=None, extended=False, page=1, limit=1):
    if not types:
        types = ['movie', 'show', 'episode']
    search_params = {
        "url": API_URL + '/search/' + ",".join(types),
        "params": {'query': query, 'extended': extended,
                   'field': 'title', 'years': year, 
                   'page': page, 'limit': limit},
    }
    r = yield 'get', search_params
    return r.json() if r else None


def get_trakt_id(title, item_type, year=None):
    required_type = 'show' if item_type == 'episode' else 'movie'

    global trakt_cache
    if not trakt_cache:
        trakt_cache = read_json(TRAKT_CACHE_PATH) or {'movie': {}, 'show': {}}

    key = f"{title}{year or ''}"

    trakt_id = trakt_cache[required_type].get(key)
    if trakt_id:
        return trakt_id

    logger.debug(f'Searching trakt: Title: "{title}"{year and f", Year: {year}" or ""}')
    results = search(title, [required_type], year)
    if results == [] and year is not None:
        # no match, possibly a mismatch in year metadata
        msg = (f'Trakt search yielded no results for the {required_type}, {title}, '
               f'Year: {year}. Retrying search without filtering by year.')
        logger.warning(msg)
        notify(msg, category="trakt")
        results = search(title, [required_type])  # retry without 'year'

    if results is None:  # Connection error
        return 0  # Dont store in cache
    elif results == [] or results[0]['score'] < 5:  # Weak or no match
        msg = f'Trakt search yielded no results for the {required_type}, {title}'
        msg += f", Year: {year}" * bool(year)
        logger.warning(msg)
        notify(msg, category="trakt")
        trakt_id = -1
    else:
        trakt_id = results[0][required_type]['ids']['trakt']

    trakt_cache[required_type][key] = trakt_id
    logger.debug(f'Trakt ID: {trakt_id}')
    write_json(trakt_cache, TRAKT_CACHE_PATH)
    return trakt_id


def get_ids(media_info):
    try:
        trakt_id = media_info['trakt_id']
    except KeyError:
        try:
            trakt_slug = media_info['trakt_slug']
        except KeyError:
            title = media_info["title"]
            trakt_id = get_trakt_id(title, media_info['type'], media_info.get('year'))
            if trakt_id < 1:
                logger.warning(f"Invalid trakt id for {title}")
                return None
            return {'trakt': trakt_id}
        else:
            return {'slug': trakt_slug}
    else:
        if trakt_id < 1:
            logger.warning(f"Invalid trakt id for {media_info}")    
            return None
        return {'trakt': trakt_id}


def prepare_scrobble_data(media_info):
    ids = get_ids(media_info)
    if ids is None:
        return
    if media_info['type'] == 'movie':
        return {'movie': {"ids": ids}}
    elif media_info['type'] == 'episode':
        return {
            'show': {"ids": ids},
            'episode': {
                'season': media_info['season'],
                'number': media_info['episode']
            }
        }


@trakt_endpoint
def scrobble(verb, media_info, progress, *args, **kwargs):
    scrobble_data = prepare_scrobble_data(media_info)
    if not scrobble_data:
        return None
    scrobble_data['progress'] = progress
    scrobble_params = {
        "url": API_URL + '/scrobble/' + verb,
        "json": scrobble_data,
    }
    scrobble_resp = yield 'post', scrobble_params

    if scrobble_resp is not None:
        if scrobble_resp.status_code == HTTPStatus.NOT_FOUND:
            logger.warning("Not found on trakt. The media info is incorrect.")
            return None
        elif scrobble_resp.status_code == HTTPStatus.CONFLICT:
            logger.warning("Scrobble already exists on trakt server.")
            return None

    return scrobble_resp.json() if scrobble_resp else False


def prepare_history_data(watched_at, media_info):
    ids = get_ids(media_info)
    if ids is None:
        return
    if type == 'movie':
        return {'movies': [{'ids': ids, 'watched_at': watched_at}]}
    else:  # TODO: Group data by show instead of sending episode-wise
        return {'shows': [
            {'ids': ids, 'seasons': [
                {'number': media_info['season'], 'episodes': [
                    {'number': media_info['episode'], 'watched_at': watched_at}]
                 }]
             }]
        }


@trakt_endpoint
def add_to_history(media_info, updated_at, *args, **kwargs):
    watched_at = dt.utcfromtimestamp(updated_at).isoformat() + 'Z'
    history = prepare_history_data(watched_at, media_info)
    if not history:
        return
    params = {
        "url": API_URL + '/sync/history',
        "json": history,
    }
    resp = yield 'post', params
    if not resp:
        return False
    added = resp.json()['added']
    return (media_info['type'] == 'movie' and added['movies'] > 0) or \
        (media_info['type'] == 'episode' and added['episodes'] > 0)
