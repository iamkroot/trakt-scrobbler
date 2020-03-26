import logging.config

import confuse
import yaml
from trakt_scrobbler.log_config import LOGGING_CONF

confuse.OrderedDict = dict
logging.config.dictConfig(LOGGING_CONF)
logger = logging.getLogger("trakt_scrobbler")
config = confuse.Configuration("trakt-scrobbler", "trakt_scrobbler")

# copy version from default config to user config if not present
temp_root = confuse.RootView(s for s in config.sources if not s.default)
if "version" not in temp_root:
    temp_root["version"] = config["version"].get()
    with open(config.user_config_path(), "w") as f:
        yaml.dump(temp_root.flatten(), f)
elif temp_root["version"].get() != config.sources[-1]["version"]:
    logger.warning(
        "Config version mismatch! Check configs at "
        f"{config.sources[-1].filename} and {config.user_config_path()}"
    )
