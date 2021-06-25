import logging.config
from trakt_scrobbler.app_dirs import DATA_DIR
file_path = DATA_DIR / "trakt_scrobbler.log"


class DuplicateMessageFilter(logging.Filter):
    """Only show the first instance of many duplicate logs by filtering out the
    other consective instances of the same message.

    Done on a per-thread basis, otherwise "Unable to connect to MPV" and "Unable
    to connect to VLC" would count as duplicates, and second one would be filtered out.

    Example (each line is a new log message, all generated in one thread):
        Some random message
        Unable to connect
        Unable to connect
        Unable to connect
        ...
        Some other message

    becomes:
        Some random message
        Unable to connect
        Some other message
    """
    MESSAGES = ("Unable to connect", "'error': 'property unavailable'")

    def __init__(self):
        # for each message to be filtered, keep track of the threads that generated it
        self.msg_history = {msg: set() for msg in self.MESSAGES}

    def filter(self, record: logging.LogRecord):
        if not isinstance(record.msg, str):
            return True

        for msg in self.MESSAGES:
            if msg in record.msg:
                val = record.thread not in self.msg_history[msg]
                self.msg_history[msg].add(record.thread)
                return val
            else:  # some other message is sent from the thread
                # we should allow the message to be logged the next time it is generated
                # by the same thread
                self.msg_history[msg].discard(record.thread)
        return True


class ModuleFilter(logging.Filter):
    """Specify the minimum log level required for the message from a module."""
    min_levels = {}

    def filter(self, record: logging.LogRecord):
        return record.levelno >= self.min_levels.get(record.module, -1)


LOGGING_CONF = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} - {levelname} - {threadName} - {module} - {message}',
            'style': '{'
        },
        'brief': {
            'format': '{levelname} - {threadName} - {module} - {message}',
            'style': '{'
        }
    },
    'filters': {
        'duplicatemessagefilter': {
            '()': DuplicateMessageFilter,
        },
        'modulesfilter': {
            '()': ModuleFilter
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': file_path,
            'maxBytes': 131072,
            'backupCount': 5,
            'mode': 'a',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filters': ['duplicatemessagefilter', 'modulesfilter']
        }
    },
    'loggers': {
        'trakt_scrobbler': {
            'handlers': ['file'],
            'level': 'DEBUG'
        }
    }
}
