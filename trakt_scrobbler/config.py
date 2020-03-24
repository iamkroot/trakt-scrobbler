import confuse
from app_dirs import CFG_DIR
import logging

logger = logging.getLogger('trakt_scrobbler')

cfg_template = {
    "version": str,
    "general": {
        "enable_notifs": confuse.Choice([True, False]),
    },
    "fileinfo": {
        "whitelist": confuse.StrSeq(),
        "include_regexes": {
            "movie": confuse.StrSeq(),
            "episode": confuse.StrSeq()
        }
    },
    "players": dict
}

config = confuse.Configuration("trakt-scrobbler")
try:
    config.set_file(CFG_DIR / "config.yml")
    config = config.get(cfg_template)
except confuse.ConfigError:
    logger.exception("Invalid configuration")
    exit(1)
