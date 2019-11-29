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


config = read_toml(CFG_DIR / 'config.toml')
if config is None:
    logger.critical("Error while reading config file. Quitting.")
    exit(1)
