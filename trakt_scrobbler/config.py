import logging
from app_dirs import CFG_DIR
from utils import read_toml

logger = logging.getLogger("trakt-scrobbler")

config = read_toml(CFG_DIR / 'config.toml')
if config is None:
    logger.critical("Error while reading config file. Quitting.")
    exit(1)
