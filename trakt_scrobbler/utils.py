import json
import locale
import logging.config
import os
import re
import sys
import threading
import time
from typing import Iterable
from functools import lru_cache, singledispatch
from urllib.parse import ParseResult, urlparse
from urllib.request import url2pathname

import confuse
import requests
from requests.packages.urllib3.util.retry import Retry
from trakt_scrobbler import config

logger = logging.getLogger('trakt_scrobbler')


def init_sess():
    proxies = config['general']['proxies'].get()
    retries = Retry(
        total=5,
        allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retries)
    sess = requests.Session()
    sess.proxies = proxies
    sess.mount("https://", adapter)
    sess.mount("http://", adapter)
    return sess


sess = init_sess()


def read_json(file_path):
    try:
        with open(file_path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f'Invalid json in {file_path}.')
    except FileNotFoundError:
        logger.debug(f"{file_path} doesn't exist.")
    return {}  # fallback to empty json


def write_json(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def safe_request(verb, params):
    """ConnectionError handling for requests methods."""
    try:
        resp = sess.request(verb, **params)
    except (requests.ConnectionError, requests.Timeout) as e:
        logger.error(f"Failed to connect: {e}")
        logger.debug(f'Request: {verb} {params}')
        return None
    if not resp.ok:
        logger.warning("Request failed")
        logger.debug(f'Request: {verb} {params}')
        logger.debug(f'Response: {resp} {resp.text}')
    return resp


@lru_cache()
@singledispatch
def is_url(parsed_path: ParseResult) -> bool:
    """Check whether the given path is a URL like 'https://example.org/path.mkv'"""
    if sys.platform == 'win32':
        # parsing "D:\path" causes scheme="D", netloc=""
        return len(parsed_path.scheme) >= 2 or parsed_path.netloc != ''
    else:  # on other platforms, it's simple
        return parsed_path.scheme != ''


@lru_cache()
@is_url.register  # overload based on type
def is_url_str(path: str) -> bool:
    try:
        return is_url(urlparse(path))
    except ValueError:
        return False


@lru_cache()
def file_uri_to_path(file_uri: str) -> str:
    """Convert a file uri to absolute path."""
    try:
        parsed = urlparse(file_uri)
        host = "{0}{0}{mnt}{0}".format(os.path.sep, mnt=parsed.netloc)
        return os.path.abspath(os.path.join(host, url2pathname(parsed.path)))
    except ValueError:
        logger.warning(f"Invalid file uri '{file_uri}'")
        return None


@lru_cache()
def cleanup_encoding(file_path: str) -> str:
    if sys.platform == "win32":
        enc = locale.getpreferredencoding()
        try:
            file_path = str(file_path).encode(enc).decode()
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            logger.debug(f"System encoding scheme: '{enc}'")
            try:
                logger.debug(f"UTF8: {str(file_path).encode('utf-8')}")
                logger.debug(f"System: {str(file_path).encode(enc)}")
            except UnicodeEncodeError as e:
                logger.debug(f"Error while logging {e!s}")
            else:
                logger.warning(f"Ignoring encoding error {e!s}")
    return file_path


class AutoloadError(Exception):
    def __init__(self, param=None, src=None, extra_msg=""):
        self.param = param
        self.src = src
        self.extra_msg = extra_msg

    def __str__(self):
        msg = "Failed to autoload value"
        if self.param:
            msg += f" for '{self.param}'"
        if self.src:
            if isinstance(self.src, Iterable) and not isinstance(self.src, str):
                src = "any of " + ", ".join(map(lambda s: f"'{s}'", self.src))
            else:
                src = f"'{self.src!s}'"
            msg += f" from {src}"
        if self.extra_msg:
            msg += ": " + self.extra_msg
        return msg


def pluralize(num: int, singular: str, plural: str = None) -> str:
    if plural is None:
        plural = singular + 's'
    return f"{num} {singular if num == 1 else plural}"


class ResumableTimer:
    def __init__(self, timeout, callback, args=None, kwargs=None):
        self.timeout = timeout
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.timer = threading.Timer(timeout, callback, args, kwargs)

    def start(self):
        self.start_time = time.time()
        self.timer.start()

    def pause(self):
        self.timer.cancel()
        self.timer = None
        self.pause_time = time.time()

    def resume(self):
        if self.timer:
            # don't resume if already running
            return
        # reduce the timeout by num of seconds for which timer was active
        self.timeout -= self.pause_time - self.start_time
        self.timer = threading.Timer(
            self.timeout, self.callback, self.args, self.kwargs)
        self.start()

    def cancel(self):
        if self.timer is not None:
            self.timer.cancel()


class RegexPat(confuse.Template):
    """A regex configuration value template"""

    def convert(self, value, view) -> re.Pattern:
        """Check that the value is an regex.
        """
        try:
            return re.compile(value)
        except re.error as e:
            self.fail(u"malformed regex: '{}' error: {}".format(e.pattern, e), view)
