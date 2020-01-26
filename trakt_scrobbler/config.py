import logging
import confuse
from app_dirs import CFG_DIR

logger = logging.getLogger("trakt_scrobbler")

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
config.set_file(CFG_DIR / "config.yml")
config = config.get(cfg_template)
