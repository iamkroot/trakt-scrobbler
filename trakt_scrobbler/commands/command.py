import re
import subprocess as sp
import sys
from cleo import Command as BaseCommand
from clikit.args import StringArgs
from clikit.io import NullIO

APP_NAME = "trakt-scrobbler"
CMD_NAME = "trakts"
platform = sys.platform


class Command(BaseCommand):
    def call_sub(self, name, args="", silent=False):
        """call() equivalent which supports subcommands"""
        names = name.split(" ")
        command = self.application.get_command(names[0])
        for name in names[1:]:
            command = command.get_sub_command(name)
        args = StringArgs(args)

        return command.run(args, silent and NullIO() or self.io)


def _get_win_pid():
    try:
        op = sp.check_output(
            [
                "wmic",
                "process",
                "where",
                f"name='{CMD_NAME}.exe'",
                "get",
                "CommandLine,ProcessID",
            ],
            text=True,
        )
        pattern = re.compile(r" run.*?(?P<pid>\d+)")
    except FileNotFoundError:
        op = sp.check_output(
            [
                "powershell",
                "-NonInteractive",
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "gwmi -Query \"select processid from win32_process where name='trakts.exe' and commandline like '%run%'\""
            ],
            text=True,
        )
        pattern = re.compile(r"ProcessId\s*:\s*(?P<pid>\d+)")
    for line in op.split("\n"):
        match = pattern.search(line)
        if match:
            return match["pid"]


def _kill_task_win(pid):
    sp.check_call(["taskkill", "/pid", pid, "/f", "/t"])
