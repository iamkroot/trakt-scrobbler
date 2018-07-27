import logging
import logging.config
import sys


class StoppedPlayersFilter(logging.Filter):
    """Limit the logging of 'Unable to connect' for players not running."""

    def __init__(self):
        self.log_count = {}

    def filter(self, record: logging.LogRecord):
        if 'Unable to connect' in record.msg:
            if record.thread not in self.log_count:
                self.log_count[record.thread] = 1
            else:
                self.log_count[record.thread] += 1
                if self.log_count[record.thread] % 100:
                    return False
        return True


class ModuleFilter(logging.Filter):
    min_levels = {
        'file_info': logging.INFO,
    }

    def filter(self, record: logging.LogRecord):
        if record.module in self.min_levels.keys() and \
           record.levelno < self.min_levels[record.module]:
            return False
        return True


LOGGING_CONF = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} - {levelname} - {module} - {message}',
            'style': '{'
        },
        'brief': {
            'format': '{levelname} - {module} - {message}',
            'style': '{'
        }
    },
    'filters': {
        'stoppedplayersfilter': {
            '()': StoppedPlayersFilter,
        },
        'modulesfilter': {
            '()': ModuleFilter
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'trakt_scrobbler.log',
            'mode': 'a',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filters': ['stoppedplayersfilter', 'modulesfilter']
        },
        'print': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'stream': sys.stdout,
            'formatter': 'brief',
            'filters': ['stoppedplayersfilter', 'modulesfilter']
        }
    },
    'loggers': {
        'trakt_scrobbler': {
            'handlers': ['file', 'print'],
            'level': 'DEBUG'
        }
    }
}
