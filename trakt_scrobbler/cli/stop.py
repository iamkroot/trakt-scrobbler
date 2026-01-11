import subprocess as sp
import sys

import typer

from .console import console
from .utils import _get_win_pid, _kill_task_win

app = typer.Typer()
platform = sys.platform


@app.command(help="Stops the trakt-scrobbler service.")
def stop():
    if platform == "darwin":
        sp.check_call(["launchctl", "stop", "com.iamkroot.trakt-scrobbler"])
    elif platform == "linux":
        sp.check_call(["systemctl", "--user", "stop", "trakt-scrobbler"])
    else:
        pid = _get_win_pid()
        if pid:
            _kill_task_win(pid)
    console.print("The monitors are stopped.")
