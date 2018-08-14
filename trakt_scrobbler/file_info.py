import logging
import re
import guessit
from pathlib import Path
from trakt_interface import search as trakt_search
from utils import config, read_json, write_json

logger = logging.getLogger('trakt_scrobbler')
trakt_cache = read_json('trakt_cache.json') or {'movie': {}, 'show': {}}


def whitelist_file(file_path):
    if not config['fileinfo'].get('whitelist'):
        return True
    parents = list(file_path.absolute().resolve().parents)
    return any(Path(path).resolve() in parents
               for path in config['fileinfo']['whitelist'])


def custom_regex(file_path):
    logger.debug('Trying to match custom regex.')
    path_posix = str(file_path.as_posix())
    for item_type, patterns in config['fileinfo']['include_regexes'].items():
        for pattern in patterns:
            m = re.match(pattern, path_posix)
            if m:
                guess = m.groupdict()
                guess['type'] = item_type
                return guess
    logger.debug('No regex matches for ' + path_posix)


def use_guessit(file_path):
    logger.debug('Using guessit module to match.')
    guess = guessit.guessit(str(file_path))
    logger.debug(guess)
    return guess


def search_cache(title):
    """Search cache for trakt ID of show or movie."""
    logger.debug('Searching cache.')
    for value in trakt_cache.values():
        if title in value:
            trakt_id = value[title]
            return trakt_id


def search_trakt(title, item_type):
    logger.debug('Searching trakt.')
    required_type = 'show' if item_type == 'episode' else 'movie'
    results = trakt_search(title, [required_type])
    if not results:
        logger.warning('Trakt search yielded no results.')
        trakt_id = None
    else:
        trakt_id = results[0][required_type]['ids']['trakt']
    trakt_cache[required_type][title] = trakt_id
    logger.debug(f'Trakt ID: {trakt_id}')
    write_json(trakt_cache, 'trakt_cache.json')
    return trakt_id


def find_file(file_path):
    guess = custom_regex(file_path)
    if not guess:
        guess = use_guessit(file_path)
    if any(key not in guess for key in ('title', 'type')) or \
       (guess['type'] == 'episode' and 'episode' not in guess):
        logger.warning('Failed to parse filename for episode/movie info. ' +
                       'Consider renaming/using custom regex.')
        return None, None
    trakt_id = search_cache(guess['title'])
    if not trakt_id:
        trakt_id = search_trakt(guess['title'], guess['type'])
    return (trakt_id, guess)


def prepare_data(trakt_id, guess):
    if guess['type'] == 'movie':
        return {'movie': {'ids': {'trakt': trakt_id}}}
    elif guess['type'] == 'episode':
        return {
            'show': {'ids': {'trakt': trakt_id}},
            'episode': {
                'season': guess.get('season', 1),
                'number': guess['episode']
            }
        }


def get_media_trakt_data(path):
    file_path = Path(path)
    logger.debug('Filepath ' + str(file_path))
    if not whitelist_file(file_path):
        logger.info("File path not in whitelist.")
        return None
    trakt_id, guess = find_file(file_path)
    if trakt_id:
        logger.info('Found Trakt ID of media.')
        return prepare_data(trakt_id, guess)
