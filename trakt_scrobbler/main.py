import inspect
import logging
import logging.config
from importlib import import_module
from pathlib import Path
from queue import Queue
from player_monitors.monitor import Monitor
from scrobbler import Scrobbler
from trakt_interface import get_access_token, read_token_data
from utils import config, LOGGING

logging.config.dictConfig(LOGGING)
logger = logging.getLogger('trakt_scrobbler')


def get_monitors():
    """Collect the monitors from 'player_monitors' subdirectory."""
    modules = Path('player_monitors').glob('*.py')
    allowed_monitors = config['players']['priorities']

    for module_path in modules:
        if module_path.stem == '__init__' or module_path.stem == 'monitor':
            continue  # exclude __init__ and base class

        # import the module
        monitor_module = import_module('player_monitors.' + module_path.stem)

        # get the required Monitor subclasses
        for _, mon in inspect.getmembers(monitor_module, inspect.isclass):
            if issubclass(mon, Monitor) and mon.name in allowed_monitors \
               and not mon.__dict__.get('exclude_import'):
                yield mon


def main():
    if not read_token_data():
        get_access_token()
    scrobble_queue = Queue()
    scrobbler = Scrobbler(scrobble_queue)
    scrobbler.start()
    for Mon in get_monitors():
        mon = Mon(scrobble_queue)
        mon.start()


if __name__ == '__main__':
    main()
