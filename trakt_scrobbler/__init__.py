import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from .log_config import LOGGING_CONF
import logging.config
logging.config.dictConfig(LOGGING_CONF)
