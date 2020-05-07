import subprocess as sp
from .command import Command, platform


class OpenLogCommand(Command):
    """
    Open the latest log file in your default editor.

    open
    """

    def handle(self):
        from trakt_scrobbler.app_dirs import DATA_DIR

        file_path = DATA_DIR / "trakt_scrobbler.log"

        if not file_path.exists():
            self.line(f'Log file not found at "{file_path}"', "error")
            return 1
        if platform == "darwin":
            sp.Popen(["open", file_path])
        elif platform == "linux":
            sp.Popen(["xdg-open", file_path])
        elif platform == "win32":
            sp.Popen(f'start "{file_path}"', shell=True)


class LogLocationCommand(Command):
    """
    Prints the location of the log file.

    path
    """

    def handle(self):
        from trakt_scrobbler.app_dirs import DATA_DIR

        file_path = DATA_DIR / "trakt_scrobbler.log"
        self.line(f'"{file_path}"')


class LogCommand(Command):
    """
    Access the log file, mainly for debugging purposes.

    log
    """

    commands = [LogLocationCommand(), OpenLogCommand()]

    def handle(self):
        return self.call("help", self._config.name)
