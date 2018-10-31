import logging
import logging.config
from utils import DATA_DIR, config


class StoppedPlayersFilter(logging.Filter):
    """Only allow the first 'Unable to connect' for players not running."""

    def __init__(self):
        self.log_count = set()

    def filter(self, record: logging.LogRecord):
        if record.threadName in config['players']['monitored']:
            if 'Unable to connect' in record.msg:
                val = record.thread not in self.log_count
                self.log_count.add(record.thread)
                return val
            else:  # some other message is sent from the thread
                self.log_count.discard(record.thread)
        return True


class ModuleFilter(logging.Filter):
    """Specify the minimum log level required for the message from a module."""
    min_levels = {}

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
            'format': '{asctime} - {levelname} - {threadName} - {module} - {message}',  # Ignore PycodestyleBear (E501)
            'style': '{'
        },
        'brief': {
            'format': '{levelname} - {threadName} - {module} - {message}',
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
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': DATA_DIR / 'trakt_scrobbler.log',
            'maxBytes': 131072,
            'backupCount': 5,
            'mode': 'a',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filters': ['stoppedplayersfilter', 'modulesfilter']
        }
    },
    'loggers': {
        'trakt_scrobbler': {
            'handlers': ['file'],
            'level': 'DEBUG'
        }
    }
}
