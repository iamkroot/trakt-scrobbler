import logging
import logging.config
import sys
import threading

from trakt_scrobbler.log_config import LOGGING_CONF
from trakt_scrobbler.__version__ import __version__  # noqa

logging.config.dictConfig(LOGGING_CONF)
logger = logging.getLogger("trakt_scrobbler")


def register_exception_handler():
    """Exception handler to log all errors from threads."""
    def error_logger(*exc_info):
        logger.exception("Unhandled exception", exc_info=exc_info)
        try:
            from trakt_scrobbler.notifier import notify
            notify(f"Check log file.\n{exc_info[1]}", "Unhandled Exception",
                   category="exception")
        except Exception:
            logger.exception("Exception while notifying user.")

    sys.excepthook = error_logger

    # from http://stackoverflow.com/a/31622038
    """
    Workaround for `sys.excepthook` thread bug from:
    http://bugs.python.org/issue1230540
    """

    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_except_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())
                return

        self.run = run_with_except_hook

    threading.Thread.__init__ = init


register_exception_handler()

from trakt_scrobbler.configuration import config
