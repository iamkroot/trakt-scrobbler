import subprocess as sp
from .command import Command, platform


class LogOpenCommand(Command):
    """
    Open the latest log file in your default editor.

    open
    """

    def handle(self):
        from trakt_scrobbler.log_config import file_path

        if not file_path.exists():
            self.line(f'Log file not found at "{file_path}"', "error")
            return 1
        self.info(f'Log file is located at: <comment>"{file_path}"</comment>')
        if platform == "darwin":
            sp.Popen(["open", file_path])
        elif platform == "linux":
            sp.Popen(["xdg-open", file_path])
        elif platform == "win32":
            sp.Popen(["explorer", file_path])
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
        from trakt_scrobbler.log_config import file_path

        self.line(f'{file_path}')


class LogCommand(Command):
    """
    Access the log file, mainly for debugging purposes.

    log
    """

    commands = [LogLocationCommand(), LogOpenCommand()]

    def handle(self):
        return self.call("help", self._config.name)
