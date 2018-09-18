import inspect
import logging
import logging.config
import sys
import threading

from importlib import import_module
from pathlib import Path
from queue import Queue

from player_monitors.monitor import Monitor
from scrobbler import Scrobbler
from trakt_interface import TRAKT_TOKEN_PATH, get_access_token
from utils import config, read_json
from log_config import LOGGING_CONF

logging.config.dictConfig(LOGGING_CONF)
logger = logging.getLogger('trakt_scrobbler')


def get_monitors():
    """Collect the monitors from 'player_monitors' subdirectory."""
    modules = Path('player_monitors').glob('*.py')
    allowed_monitors = config['players']['monitored']

    for module_path in modules:
        if module_path.stem == '__init__' or module_path.stem == 'monitor':
            continue  # exclude __init__ and base module

        monitor_module = import_module('player_monitors.' + module_path.stem)
        # get the required Monitor subclasses
        for _, mon in inspect.getmembers(monitor_module, inspect.isclass):
            if issubclass(mon, Monitor) and mon.name in allowed_monitors \
               and not getattr(mon, 'exclude_import', False):
                yield mon


def register_exception_handler():
    """Exception handler to log all errors from threads."""
    def error_logger(*exc_info):
        logger.exception('Unhandled exception', exc_info=exc_info)

    sys.excepthook = error_logger

    # from http://stackoverflow.com/a/31622038
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540
    Call once from the main thread before creating any threads.
    """

    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception as e:
                sys.excepthook(*sys.exc_info())
                return

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


def main():
    register_exception_handler()
    if not read_json(TRAKT_TOKEN_PATH):
        get_access_token()
    scrobble_queue = Queue()
    scrobbler = Scrobbler(scrobble_queue)
    scrobbler.start()
    for Mon in get_monitors():
        mon = Mon(scrobble_queue)
        mon.start()


if __name__ == '__main__':
    main()
