import inspect
from importlib import import_module
import logging.config
from pathlib import Path
from queue import Queue
from utils import config, LOGGING
from scrobbler import Scrobbler
from player_monitors.monitor import Monitor

logging.config.dictConfig(LOGGING)


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
    q = Queue()
    scrobbler = Scrobbler(q)
    scrobbler.start()
    for Mon in get_monitors():
        mon = Mon(q)
        mon.start()


if __name__ == '__main__':
    main()
