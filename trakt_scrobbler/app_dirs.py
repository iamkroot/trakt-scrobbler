import appdirs
from pathlib import Path

NAME = "trakt-scrobbler"
DATA_DIR = Path(appdirs.user_data_dir(NAME, appauthor=False, roaming=True))
CFG_DIR = Path(appdirs.user_config_dir(NAME, appauthor=False, roaming=True))
DATA_DIR.mkdir(exist_ok=True, parents=True)
CFG_DIR.mkdir(exist_ok=True, parents=True)
