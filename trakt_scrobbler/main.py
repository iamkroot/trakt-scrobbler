import inspect
import importlib
import logging.config
from pathlib import Path
from queue import Queue
from players.player import Player
from player_monitor import Monitor
from scrobbler import Scrobbler
from utils import config, LOGGING

logging.config.dictConfig(LOGGING)


def get_players():
    """Collect the player classes from 'players' subdirectory."""
    modules = Path('players').glob('*.py')

    for module_path in modules:
        if module_path.stem == '__init__' or module_path.stem == 'player':
            continue  # exclude __init__ and base class

        # import the module
        player_module = importlib.import_module('players.' + module_path.stem)

        # get the required Player subclasses
        for _, player in inspect.getmembers(player_module, inspect.isclass):
            if issubclass(player, Player) and not player == Player and \
               player.name in config['players']['priorities']:
                yield player


def main():
    q = Queue()
    scrobbler = Scrobbler(q)
    scrobbler.start()

    # Start a monitor thread for each player as per config
    for player in get_players():
        monitor = Monitor(player(), q)
        monitor.start()


if __name__ == '__main__':
    main()
