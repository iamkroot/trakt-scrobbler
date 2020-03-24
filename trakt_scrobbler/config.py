import confuse
from app_dirs import CFG_DIR
import logging

logger = logging.getLogger('trakt_scrobbler')

cfg_template = {
    "version": confuse.String(),
    "general": {"enable_notifs": confuse.Choice([True, False], default=True),},
    "fileinfo": {
        "whitelist": confuse.StrSeq(default=[]),
        "include_regexes": {
            "movie": confuse.StrSeq(default=[]),
            "episode": confuse.StrSeq(default=[]),
        },
    },
    "players": {
        "monitored": confuse.StrSeq(default=[]),
        "skip_interval": confuse.Number(default=5),
        "vlc": {
            "ip": confuse.String(default="localhost"),
            "port": confuse.String(default="auto-detect"),
            "password": confuse.String(default="auto-detect"),
            "poll_interval": confuse.Number(default=10),
        },
        "mpv": {
            "ipc_path": confuse.String(default="auto-detect"),
            "poll_interval": confuse.Number(default=10),
        },
        "mpc-hc": {
            "ip": confuse.String(default="localhost"),
            "port": confuse.String(default="auto-detect"),
            "poll_interval": confuse.Number(default=10),
        },
        "mpc-be": {
            "ip": confuse.String(default="localhost"),
            "port": confuse.String(default="auto-detect"),
            "poll_interval": confuse.Number(default=10),
        },
        "plex": {
            "ip": confuse.String(default="localhost"),
            "port": confuse.String(default="32400"),
            "login": confuse.String(default=""),
            "password": confuse.String(default=""),
            "poll_interval": confuse.Number(default=10),
        }
    },
}

config = confuse.Configuration("trakt-scrobbler")
try:
    config.set_file(CFG_DIR / "config.yml")
    config = config.get(cfg_template)
except confuse.ConfigError:
    logger.exception("Invalid configuration")
    exit(1)
