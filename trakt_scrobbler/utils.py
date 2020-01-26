import json
import locale
import logging.config
import sys
import toml
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote

logger = logging.getLogger('trakt_scrobbler')


def read_toml(file_path: Path):
    try:
        return toml.load(file_path)
    except toml.TomlDecodeError:
        logger.error(f'Invalid TOML in {file_path}.')
    except FileNotFoundError:
        logger.error(f"{file_path} doesn't exist.")


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
        resp = requests.request(verb, **params)
    except requests.exceptions.ConnectionError:
        logger.exception('Failed to connect.')
        logger.debug(f'Request: {verb} {params}')
        return None
    if not resp.ok:
        logger.warning("Request failed")
        logger.debug(f'Request: {verb} {params}')
        logger.debug(f'Response: {resp} {resp.text}')
    else:
        return resp


def file_uri_to_path(file_uri):
    if not file_uri.startswith('file://'):
        logger.warning(f"Invalid file uri '{file_uri}'")
        return None
    path = urlparse(unquote(file_uri)).path
    if sys.platform == 'win32' and path.startswith('/'):
        path = path[1:]
    return path


def cleanup_encoding(file_path: Path):
    if sys.platform == "win32":
        enc = locale.getpreferredencoding()
        try:
            file_path = Path(str(file_path).encode(enc).decode())
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
    def __init__(self, param=None, src=None):
        self.param = param
        self.src = src

    def __str__(self):
        msg = "Failed to autoload value"
        if self.param:
            msg += f" for '{self.param}'"
        if self.src:
            msg += f" from '{self.src}'"
        return msg
