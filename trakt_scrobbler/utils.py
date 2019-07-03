import json
import logging
import sys
import toml
import requests
from pathlib import Path

logger = logging.getLogger('trakt_scrobbler')


def get_dirs():
    NAME = 'trakt-scrobbler'
    DATA_DIR = None

    def dir_path(path: str) -> Path:
        return Path(path).expanduser() / NAME

    if sys.platform == 'win32':
        DATA_DIR = dir_path('~/AppData/Roaming')
        CFG_DIR = DATA_DIR
    elif sys.platform == 'linux':
        DATA_DIR = dir_path('~/.local/share')
        CFG_DIR = dir_path('~/.config')
    elif sys.platform == 'darwin':
        DATA_DIR = dir_path('~/Library/Application Support')
        CFG_DIR = dir_path('~/Library/Preferences')
    else:
        logger.error('Unknown OS')
        exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR, CFG_DIR


DATA_DIR, CFG_DIR = get_dirs()


def read_config(config_path):
    try:
        with open(config_path) as f:
            try:
                return toml.load(f)
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
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f'Invalid json in {file_path}.')
                return None
    except FileNotFoundError:
        logger.warning(f"{file_path} doesn't exist.")
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
