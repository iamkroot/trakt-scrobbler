from datetime import datetime as dt
from http import HTTPStatus
from trakt_scrobbler import logger
from trakt_scrobbler.app_dirs import DATA_DIR
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.trakt_auth import API_URL, TraktAuth
from trakt_scrobbler.utils import safe_request, read_json, write_json

trakt_auth = TraktAuth()
TRAKT_CACHE_PATH = DATA_DIR / 'trakt_cache.json'
trakt_cache = {}


def search(query, types=None, year=None, extended=False, page=1, limit=1):
    if not types:
        types = ['movie', 'show', 'episode']
    search_params = {
        "url": API_URL + '/search/' + ",".join(types),
        "params": {'query': query, 'extended': extended,
                   'field': 'title', 'years': year, 
                   'page': page, 'limit': limit},
        "headers": trakt_auth.headers
    }
    r = safe_request('get', search_params)
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
        "json": scrobble_data,
        "timeout": 30,
    }
    scrobble_resp = safe_request('post', scrobble_params)

    if scrobble_resp is not None:
        if scrobble_resp.status_code == HTTPStatus.NOT_FOUND:
            logger.warning("Not found on trakt. The media info is incorrect.")
            return None
        elif scrobble_resp.status_code == HTTPStatus.CONFLICT:
            logger.warning("Scrobble already exists on trakt server.")
            return None

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
        "json": history,
        "timeout": 30,
    }
    resp = safe_request('post', params)
    if not resp:
        return False
    added = resp.json()['added']
    return (media_info['type'] == 'movie' and added['movies'] > 0) or \
        (media_info['type'] == 'episode' and added['episodes'] > 0)
