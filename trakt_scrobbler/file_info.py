from functools import lru_cache
from typing import Tuple, Union, List
from urllib.parse import unquote, urlsplit, urlunsplit

import confuse
import guessit
from trakt_scrobbler import config, logger
from trakt_scrobbler.configuration import AnyDictValTemplate, BoolTemplate, RegexPat
from trakt_scrobbler.utils import cleanup_encoding, is_url
from urlmatch import BadMatchPattern, urlmatch


class WhitelistTemplate(confuse.Template):
    """Parse the whitelist comprising of local and remote patterns."""
    def convert(self, value, view) -> Tuple[List[str], List[str]]:
        whitelist = confuse.StrSeq(split=False).convert(value, view)
        local, remote = [], []
        for path in whitelist:
            try:
                urlmatch(path, "<dummy_path>", path_required=False, fuzzy_scheme=True)
                # ignore result
            except BadMatchPattern:
                # local paths will raise BadMatchPattern error
                local.append(path)
            else:
                remote.append(path)
        return local, remote


# set up the config variable handles
cfg = config["fileinfo"]
split_whitelist = cfg["whitelist"].get_handle(WhitelistTemplate())
any_whitelist = cfg["whitelist"].get_handle(BoolTemplate())
regexes = cfg['include_regexes'].get_handle({
    "movie": confuse.Sequence(RegexPat()),
    "episode": confuse.Sequence(RegexPat()),
})

use_regex = cfg['include_regexes'].get_handle(AnyDictValTemplate({'movie', 'episode'}))
exclude_patterns = cfg["exclude_patterns"].get_handle(confuse.Sequence(RegexPat()))


def whitelist_local(local_path: str, file_path: str) -> bool:
    """
    Simply checks that the whitelist path should be prefix of file_path.

    An edge case that is deliberately not handled:
    Suppose user has whitelisted "path/to/tv" directory
    and the user also has another directory "path/to/tv shows".
    If the user plays something from the latter, it will still be whitelisted.
    """
    return file_path.startswith(local_path)


def whitelist_remote(whitelist_path: str, file_path: str) -> bool:
    return urlmatch(whitelist_path, file_path, path_required=False, fuzzy_scheme=True)


def whitelist_file(file_path: str, is_url=False, return_path=False) -> Union[bool, str]:
    """Check if the played media file is in the allowed list of paths"""
    if not any_whitelist.get():
        return True
    is_whitelisted = whitelist_remote if is_url else whitelist_local
    local_paths, remote_paths = split_whitelist.get()
    whitelist_paths = remote_paths if is_url else local_paths

    for path in whitelist_paths:
        if is_whitelisted(path, file_path):
            logger.debug(f"Matched whitelist entry {path!r}")
            return path if return_path else True

    return False


def exclude_file(file_path: str) -> bool:
    for pattern in exclude_patterns.get():
        if pattern.match(file_path):
            logger.debug(f"Matched exclude pattern {pattern!r}")
            return True
    return False


def custom_regex(file_path: str):
    for item_type, patterns in regexes.get().items():
        for pattern in patterns:
            m = pattern.match(file_path)
            if m:
                logger.debug(f"Matched regex pattern {pattern!r}")
                guess = m.groupdict()
                guess['type'] = item_type
                return guess


def use_guessit(file_path: str):
    try:
        return guessit.guessit(file_path)
    except guessit.api.GuessitException:
        # lazy import the notifier module
        # This codepath will not be executed 99.99% of the time, and importing notify
        # in the outer scope is expensive due to the categories parsing
        # It is unneeded when using the "trakts whitelist" command
        from trakt_scrobbler.notifier import notify
        logger.exception("Encountered guessit error.")
        notify("Encountered guessit error. File a bug report!", category="exception")
        return {}


@lru_cache(maxsize=None)
def get_media_info(file_path: str):
    logger.debug(f"Raw filepath {file_path!r}")
    file_path = cleanup_encoding(file_path)
    parsed = urlsplit(file_path)
    file_is_url = False
    guessit_path = file_path
    if is_url(parsed):
        file_is_url = True
        # remove the query and fragment from the url, keeping only important parts
        scheme, netloc, path, _, _ = parsed
        path = unquote(path)  # quoting should only be applied to the path
        file_path = urlunsplit((scheme, netloc, path, "", ""))
        logger.debug(f"Converted to url {file_path!r}")
        # only use the actual path for guessit, skipping other parts
        guessit_path = path
        logger.debug(f"Guessit url {guessit_path!r}")

    if not whitelist_file(file_path, file_is_url):
        logger.info("File path not in whitelist.")
        return None
    if exclude_file(file_path):
        logger.info("Ignoring file.")
        return None
    guess = use_regex.get() and custom_regex(file_path) or use_guessit(guessit_path)
    logger.debug(f"Guess: {guess}")
    return cleanup_guess(guess)


def cleanup_guess(guess):
    if not guess:
        return None

    if any(key not in guess for key in ('title', 'type')) or \
       (guess['type'] == 'episode' and 'episode' not in guess):
        logger.warning('Failed to parse filename for episode/movie info. '
                       'Consider renaming/using custom regex.')
        return None

    if isinstance(guess['title'], list):
        guess['title'] = " ".join(guess['title'])

    req_keys = ['type', 'title']
    if guess['type'] == 'episode':
        season = guess.get('season')
        if season is None:
            # if we don't find a season, default to 1
            season = 1  # TODO: Add proper support for absolute-numbered episodes
        if isinstance(season, list):
            from trakt_scrobbler.notifier import notify
            msg = f"Multiple probable seasons found: ({','.join(map(str, season))}). "
            msg += "Consider renaming the folder."
            logger.warning(msg)
            notify(msg)
            return None
        guess['season'] = int(season)
        req_keys += ['season', 'episode']

    if 'year' in guess:
        req_keys += ['year']

    return {key: guess[key] for key in req_keys}
