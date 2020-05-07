import subprocess as sp
from .command import Command, platform, _get_win_pid, _kill_task_win


class StopCommand(Command):
    """
    Stops the trakt-scrobbler service.

    stop
    """

    def handle(self):
        if platform == "darwin":
            sp.check_call(["launchctl", "stop", "com.iamkroot.trakt-scrobbler"])
        elif platform == "linux":
            sp.check_call(["systemctl", "--user", "stop", "trakt-scrobbler"])
        else:
            pid = _get_win_pid()
            if pid:
                _kill_task_win(pid)
        self.line("The monitors are stopped.")
