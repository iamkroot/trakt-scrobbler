import logging.config
import confuse
from trakt_scrobbler.log_config import LOGGING_CONF
confuse.OrderedDict = dict
logging.config.dictConfig(LOGGING_CONF)
logger = logging.getLogger("trakt_scrobbler")
config = confuse.Configuration("trakt-scrobbler", "trakt_scrobbler")
