import shutil
import subprocess as sp
from .command import CMD_NAME, Command, platform, _get_win_pid, _kill_task_win


class StartCommand(Command):
    """
    Starts the trakt-scrobbler service. If already running, does nothing.

    start
        {--r|restart : Restart the service}
    """

    def handle(self):
        restart = self.option("restart")
        if platform == "darwin":
            if restart:
                sp.check_call(["launchctl", "stop", "com.iamkroot.trakt-scrobbler"])
            sp.check_call(["launchctl", "start", "com.iamkroot.trakt-scrobbler"])
        elif platform == "linux":
            cmd = "restart" if restart else "start"
            sp.check_call(["systemctl", "--user", cmd, "trakt-scrobbler"])
        else:
            pid = _get_win_pid()
            if pid and restart:
                _kill_task_win(pid)
                pid = None
            if not pid:
                sp.check_call(
                    f'start "trakt-scrobbler" /B "{shutil.which(CMD_NAME)}" run',
                    shell=True,
                )
        self.line("The monitors are running.")
