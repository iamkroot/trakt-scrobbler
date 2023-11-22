import logging
import logging.config
import sys
import threading

import confuse
import yaml

# For reasons beyond my understanding, we cannot instantiate
# DesktopNotifier _after_ we have imported pythoncom on Windows.
# Trying to do so gives error "The application called an interface that was marshalled for a different thread"
# 
# Possibly a conflict between win32 (pythoncom) and winrt (notifier) APIs.
# 
# So workaround is to instantiate the notifier _before_ any other import happens
APP_NAME = 'Trakt Scrobbler'
from desktop_notifier.main import DesktopNotifier

notifier = DesktopNotifier(APP_NAME)
if sys.platform == 'win32':
    # this is another workaround for windows.
    # See https://github.com/samschott/desktop-notifier/issues/95
    notifier._did_request_authorisation = True
# else:
#     # can be initialized later
#     notifier = None

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

    def thread_excepthook(args):
        if args.exc_type == SystemExit:
            # ignore SystemExit
            return
        error_logger(*args)

    sys.excepthook = error_logger
    threading.excepthook = thread_excepthook

    # monkey-patch the start method to log RuntimeError
    # This is needed for python 3.12 due to some interpreter errors.
    # adapted from http://stackoverflow.com/a/31622038
    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        start_original = self.start

        def start_with_except_hook(*args2, **kwargs2):
            try:
                start_original(*args2, **kwargs2)
            except RuntimeError:
                logger.exception("Runtime error in Thread start")

        self.start = start_with_except_hook

    threading.Thread.__init__ = init

    init_original_2 = threading.Timer.__init__

    def init(self, *args, **kwargs):
        init_original_2(self, *args, **kwargs)
        start_original = self.start

        def start_with_except_hook(*args2, **kwargs2):
            try:
                return start_original(*args2, **kwargs2)
            except RuntimeError:
                logger.exception("Runtime error in Timer start")

        self.start = start_with_except_hook

    threading.Timer.__init__ = init


register_exception_handler()

config = confuse.Configuration("trakt-scrobbler", "trakt_scrobbler")

# copy version from default config to user config if not present
temp_root = confuse.RootView(s for s in config.sources if not s.default)
if "version" not in temp_root:
    temp_root["version"] = config["version"].get()
    with open(config.user_config_path(), "w") as f:
        yaml.dump(temp_root.flatten(), f, Dumper=confuse.yaml_util.Dumper)
elif temp_root["version"].get() != config.sources[-1]["version"]:
    logger.warning(
        "Config version mismatch! Check configs at "
        f"{config.sources[-1].filename} and {config.user_config_path()}"
    )
