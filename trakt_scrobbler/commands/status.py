import re
import subprocess as sp
from datetime import datetime
from .command import Command, platform, _get_win_pid


def check_running():
    if platform == "darwin":
        output = sp.check_output(
            ["launchctl", "list", "com.iamkroot.trakt-scrobbler"], text=True,
        )
        for line in output.splitlines():
            if "trakt-scrobbler" in line:
                return line.strip().startswith("-")
        return False
    elif platform == "linux":
        return bool(
            sp.call(
                ["systemctl", "--user", "is-active", "--quiet", "trakt-scrobbler"]
            )
        )
    else:
        return _get_win_pid() is None


def read_log_files():
    """Returns all lines in log files, most recent first"""
    from trakt_scrobbler.app_dirs import DATA_DIR

    log_file = DATA_DIR / "trakt_scrobbler.log"
    for file in (
        log_file,
        *(log_file.with_suffix(f".log.{i}") for i in range(1, 6)),
    ):
        if not file.exists():
            return
        for line in reversed(file.read_text().splitlines()):
            yield line


class StatusCommand(Command):
    """
    Shows the status trakt-scrobbler service.

    status
    """

    def get_last_action(self):
        PAT = re.compile(
            r"(?P<asctime>.*?) -.*Scrobble (?P<verb>\w+) successful for (?P<name>.*)"
        )

        for line in read_log_files():
            match = PAT.match(line)
            if match:
                time = datetime.strptime(match["asctime"], "%Y-%m-%d %H:%M:%S,%f")
                self.line(
                    "Last successful scrobble: {verb} {name}, at {time:%c}".format(
                        time=time, verb=match["verb"].title(), name=match["name"]
                    )
                )
                break
        else:
            self.line("No activity yet.")

    def handle(self):
        # TODO: What if it is paused?        
        self.line(f"The scrobbler is {'not ' * check_running()}running")

        from trakt_scrobbler import config

        monitored = config['players']['monitored'].get()
        self.line(f"Monitored players: {', '.join(monitored)}")

        self.get_last_action()
