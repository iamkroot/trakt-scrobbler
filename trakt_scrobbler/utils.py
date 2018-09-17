import json
import logging
import pytoml
import requests
from pathlib import Path

DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
logger = logging.getLogger('trakt_scrobbler')


def read_config(config_path=DATA_DIR / 'config.toml'):
    with open(config_path) as f:
        return pytoml.load(f)


config = read_config()


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
