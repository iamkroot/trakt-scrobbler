import re
import confuse
import guessit
from functools import lru_cache
from pathlib import Path
from trakt_scrobbler import config, logger
from trakt_scrobbler.utils import cleanup_encoding


class PathSeq(confuse.Template):
    def convert(self, value, view):
        if not isinstance(value, list):
            self.fail("must be sequence.", view, True)
        paths = []
        for i, path in enumerate(value):
            try:
                paths.append(Path(path).resolve())
            except TypeError:
                self.fail(f'must be a valid path: "{path}", index: {i}', view, True)
        return paths


whitelist = config["fileinfo"]["whitelist"].get(PathSeq(default=[]))
regexes = config["fileinfo"]['include_regexes'].get()


def whitelist_file(file_path) -> bool:
    if not whitelist:
        return True
    file_path = cleanup_encoding(file_path)
    parents = tuple(file_path.absolute().resolve().parents)
    return any(path in parents for path in whitelist)


def custom_regex(file_path):
    logger.debug('Trying to match custom regex.')
    path_posix = str(file_path.as_posix())
    for item_type, patterns in regexes.items():
        for pattern in patterns:
            m = re.match(pattern, path_posix)
            if m:
                logger.debug(f"Matched pattern '{pattern}' for '{path_posix}'")
                guess = m.groupdict()
                guess['type'] = item_type
                return guess


def use_guessit(file_path):
    logger.debug('Using guessit module to match.')
    guess = guessit.guessit(str(file_path))
    logger.debug(guess)
    return guess


@lru_cache(maxsize=None)
def get_media_info(file_path):
    logger.debug(f"Filepath '{file_path}'")
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

    if isinstance(guess['title'], list):
        guess['title'] = " ".join(guess['title'])

    req_keys = ['type', 'title']
    if guess['type'] == 'episode':
        season = guess.get('season', 1)
        if isinstance(season, list):
            logger.warning(f"Multiple probable seasons found: ({','.join(season)}). "
                           "Consider renaming the folder.")
            return None
        guess['season'] = int(season)
        req_keys += ['season', 'episode']

    return {key: guess[key] for key in req_keys}
