import json
import logging
import pytoml
import requests
from pathlib import Path


def read_config(config_path='config.toml'):
    with open(config_path) as f:
        return pytoml.load(f)


def save_config(config, config_path='config.toml'):
    with open(config_path, 'w') as f:
        pytoml.dump(config, f)


def read_cache(cache_path=Path('cache.json')):
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)
    else:
        return {'movie': {}, 'show': {}}


def update_cache(cache):
    with open('cache.json', 'w') as f:
        json.dump(cache, f, indent=4)


config = read_config()
cache = read_cache()


class FilterStoppedPlayers(logging.Filter):
    """Limit the logging of 'Unable to connect' for players not running."""

    def __init__(self):
        self.log_count = {}

    def filter(self, record: logging.LogRecord):
        if record.threadName not in config['players']['priorities']:
            return True
        if 'Unable to connect' in record.msg:
            if record.thread not in self.log_count:
                self.log_count[record.thread] = 1
            else:
                self.log_count[record.thread] += 1
                if self.log_count[record.thread] % 100:
                    return False
        return True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname:8s} {asctime} {module} {message}',
            'style': '{'
        }
    },
    'filters': {
        'stoppedplayersfilter': {
            '()': FilterStoppedPlayers,
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'trakt_scrobbler.log',
            'mode': 'a',
            'formatter': 'verbose',
            'filters': ['stoppedplayersfilter']
        }
    },
    'loggers': {
        'trakt_scrobbler': {
            'level': 'DEBUG',
            'handlers': ['file']
        }
    }
}


logger = logging.getLogger('trakt_scrobbler')


def safe_request(verb, params):
    """ConnectionError handling for requests methods."""
    try:
        resp = requests.request(verb, **params)
    except requests.exceptions.ConnectionError:
        logger.error('Failed to connect.')
        logger.debug(verb + str(params))
        return None
    else:
        return resp


if __name__ == '__main__':
    pass
