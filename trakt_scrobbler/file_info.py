import logging
import re
import guessit
from functools import lru_cache
from pathlib import Path
from utils import config

logger = logging.getLogger('trakt_scrobbler')


def whitelist_file(file_path):
    if not config['fileinfo'].get('whitelist'):
        return True
    parents = list(file_path.absolute().resolve().parents)
    return any(Path(path).resolve() in parents
               for path in config['fileinfo']['whitelist'])


def custom_regex(file_path):
    logger.debug('Trying to match custom regex.')
    regexes = config['fileinfo'].get('include_regexes', {})
    path_posix = str(file_path.as_posix())
    for item_type, patterns in regexes.items():
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


@lru_cache(maxsize=None)
def get_media_info(file_path):
    logger.debug(f'Filepath {file_path}')
    file_path = Path(file_path)
    if not whitelist_file(file_path):
        logger.info("File path not in whitelist.")
        return None
    guess = custom_regex(file_path) or use_guessit(file_path)

    if any(key not in guess for key in ('title', 'type')) or \
       (guess['type'] == 'episode' and 'episode' not in guess):
        logger.warning('Failed to parse filename for episode/movie info. '
                       'Consider renaming/using custom regex.')
        return None

    req_keys = ['type', 'title']
    if guess['type'] == 'episode':
        guess['episode'] = int(guess['episode'])
        guess['season'] = int(guess.get('season', 1))
        req_keys += ['season', 'episode']

    return {key: guess[key] for key in req_keys}
