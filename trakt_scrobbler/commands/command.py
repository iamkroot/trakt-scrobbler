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
    from psutil import pids, Process
    for pid in pids():
        proc = Process(pid)
        if proc.name() == f'{CMD_NAME}.exe' and "run" in proc.cmdline():
            return pid


def _kill_task_win(pid):
    import psutil
    psutil.Process(pid).kill()
