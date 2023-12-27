import subprocess as sp
from .command import Command, platform


class LogOpenCommand(Command):
    """
    Open the latest log file in your default editor.

    open
    """

    def handle(self):
        from trakt_scrobbler.log_config import LOG_PATH

        if not LOG_PATH.exists():
            self.line(f'Log file not found at "{LOG_PATH}"', "error")
            return 1
        self.info(f'Log file is located at: <comment>"{LOG_PATH}"</comment>')
        if platform == "darwin":
            sp.Popen(["open", LOG_PATH])
        elif platform == "linux":
            sp.Popen(["xdg-open", LOG_PATH])
        elif platform == "win32":
            sp.Popen(["explorer", LOG_PATH])
        self.line(
            "In case this command doesn't work, "
            "manually open the log file from the path."
        )


class LogLocationCommand(Command):
    """
    Prints the location of the log file.

    path
    """

    def handle(self):
        from trakt_scrobbler.log_config import LOG_PATH

        self.line(f'{LOG_PATH}')


class LogCommand(Command):
    """
    Access the log file, mainly for debugging purposes.

    log
    """

    commands = [LogLocationCommand(), LogOpenCommand()]

    def handle(self):
        return self.call("help", self._config.name)
