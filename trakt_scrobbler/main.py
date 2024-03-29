from queue import Queue
import confuse
from trakt_scrobbler import config, logger
from trakt_scrobbler.backlog_cleaner import BacklogCleaner
from trakt_scrobbler.log_config import LOG_PATH
from trakt_scrobbler.notifier import notify
from trakt_scrobbler.player_monitors import collect_monitors
from trakt_scrobbler.scrobbler import Scrobbler


def main():
    scrobble_queue = Queue()
    backlog_cleaner = BacklogCleaner()
    scrobbler = Scrobbler(scrobble_queue, backlog_cleaner)
    scrobbler.start()

    allowed_monitors = config['players']['monitored'].get(confuse.StrSeq(default=[]))
    all_monitors = collect_monitors()

    unknown = set(allowed_monitors).difference(Mon.name for Mon in all_monitors)
    if unknown:
        logger.warning(f"Unknown player(s): {', '.join(unknown)}")

    threads = []
    for Mon in all_monitors:
        if Mon.name not in allowed_monitors:
            continue
        mon = Mon(scrobble_queue)
        if not mon or not mon._initialized:
            logger.warning(f"Could not start monitor for {Mon.name}")
            continue
        mon.start()
        threads.append(mon)

    for t in threads:
        # will exit when monitors die
        t.join()
    logger.critical("Exiting scrobbler - no more monitors")
    notify(f"monitors dead - trakts log open ({LOG_PATH})", category="exception")



if __name__ == '__main__':
    main()
