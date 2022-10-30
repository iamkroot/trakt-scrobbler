import logging
import logging.config
import sys
import threading

import confuse
import yaml
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

    def thread_excepthook(args: threading.ExceptHookArgs):
        if args.exc_type == SystemExit:
            # ignore SystemExit
            return
        error_logger(*args)

    sys.excepthook = error_logger

    if sys.version_info >= (3, 8):
        threading.excepthook = thread_excepthook
    else:
        # monkey-patch the excepthook mechanism into Thread class
        # from http://stackoverflow.com/a/31622038
        init_original = threading.Thread.__init__

        def init(self, *args, **kwargs):
            init_original(self, *args, **kwargs)
            run_original = self.run

            def run_with_except_hook(*args2, **kwargs2):
                try:
                    run_original(*args2, **kwargs2)
                except Exception:
                    thread_excepthook((*sys.exc_info(), self))

            self.run = run_with_except_hook

        threading.Thread.__init__ = init


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
