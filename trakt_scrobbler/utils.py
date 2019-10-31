import json
import logging.config
import sys
import toml
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote
from app_dirs import CFG_DIR
from log_config import LOGGING_CONF
logging.config.dictConfig(LOGGING_CONF)
logger = logging.getLogger('trakt_scrobbler')


def read_config(config_path: Path):
    try:
        return toml.load(config_path)
    except toml.TomlDecodeError:
        logger.error('Unable to load config.toml!')
        exit(1)
    except FileNotFoundError:
        logger.error('config.toml not found!')
        exit(1)


config = read_config(CFG_DIR / 'config.toml')


def read_json(file_path):
    try:
        with open(file_path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.warning(f'Invalid json in {file_path}.')
        return None
    except FileNotFoundError:
        logger.debug(f"{file_path} doesn't exist.")
        return None


def write_json(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


def safe_request(verb, params):
    """ConnectionError handling for requests methods."""
    try:
        resp = requests.request(verb, **params)
    except requests.exceptions.ConnectionError:
        logger.error('Failed to connect.')
        logger.debug(f'Request: {verb} {params}')
        return None
    else:
        return resp


def file_uri_to_path(file_uri):
    if not file_uri.startswith('file://'):
            return None
    path = urlparse(unquote(file_uri)).path
    if sys.platform == 'win32' and path.startswith('/'):
        path = path[1:]
    return path
