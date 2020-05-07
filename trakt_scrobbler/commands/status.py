import re
import subprocess as sp
from datetime import datetime
from .command import Command, platform, _get_win_pid


class StatusCommand(Command):
    """
    Shows the status trakt-scrobbler service.

    status
    """

    def check_running(self):
        is_inactive = False
        if platform == "darwin":
            output = sp.check_output(
                ["launchctl", "list", "com.iamkroot.trakt-scrobbler"], text=True,
            ).split("\n")
            for line in output:
                if "trakt-scrobbler" in line:
                    is_inactive = line.strip().startswith("-")
                    break
        elif platform == "linux":
            is_inactive = bool(
                sp.call(
                    ["systemctl", "--user", "is-active", "--quiet", "trakt-scrobbler"]
                )
            )
        else:
            is_inactive = _get_win_pid() is None
        self.line(f"The scrobbler is {'not ' * is_inactive}running")

    def get_last_action(self):
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
                for line in reversed(file.read_text().split("\n")):
                    yield line

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
        self.check_running()

        from trakt_scrobbler import config

        monitored = config['players']['monitored'].get()
        self.line(f"Monitored players: {', '.join(monitored)}")

        self.get_last_action()
