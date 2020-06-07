from pathlib import Path
from .command import Command
from .config import ConfigCommand


class WhitelistAddCommand(Command):
    """
    Add folder(s) to whitelist.

    add
        {folder* : Folder to be whitelisted}
    """

    def _add_single(self, folder: str):
        try:
            fold = Path(folder)
        except ValueError:
            self.line_error(f"Invalid folder {folder}")
            return
        if not fold.exists() and not self.confirm(
            f"Folder {fold} does not exist. Are you sure you want to add it?"
        ):
            return
        folder = str(fold.absolute().resolve())
        if folder.endswith("\\"):  # fix string escaping
            folder += "\\"
        self.call_sub("config set", f'--add fileinfo.whitelist "{folder}"', silent=True)
        self.line(f"<comment>{folder}</comment> added to whitelist.")

    def handle(self):
        for folder in self.argument("folder"):
            self._add_single(folder)
        self.line("Don't forget to restart the service for the changes to take effect.")


class WhitelistShowCommand(Command):
    """
    Show the current whitelist.

    show
    """

    def handle(self):
        from trakt_scrobbler import config
        import confuse

        whitelist = config["fileinfo"]["whitelist"].get(confuse.StrSeq(default=[]))
        if not whitelist:
            self.line("Whitelist empty!")
            return

        self.info("Whitelist:")
        for path in whitelist:
            self.line(path)
        self.line("Don't forget to restart the service for any changes to take effect.")


class WhitelistRemoveCommand(Command):
    """
    Remove folder(s) from whitelist (interactive).

    remove
    """

    def handle(self):
        from trakt_scrobbler import config
        import confuse

        whitelist = config["fileinfo"]["whitelist"].get(confuse.StrSeq(default=[]))
        if not whitelist:
            self.line("Whitelist empty!")
            return

        choices = self.choice(
            "Select the folders to be removed from whitelist", whitelist, multiple=True
        )
        if not self.confirm(
            f"This will remove {', '.join(choices)} from whitelist. Continue?",
            default=True,
        ):
            self.line("Aborted", "error")
            return
        for choice in choices:
            whitelist.remove(choice)
        config["fileinfo"]["whitelist"] = whitelist

        ConfigCommand.save_config(config)

        self.call_sub("whitelist show")


class WhitelistTestCommand(Command):
    """
    Check whether the given file/folder is whitelisted.

    test
        {path : File/folder to be tested}
    """

    def handle(self):
        from trakt_scrobbler.file_info import whitelist_file

        path = self.argument("path")
        try:
            path = Path(path)
        except ValueError:
            self.line_error(f"Invalid path '{path}'")
            return 1
        whitelist_path = whitelist_file(path)
        if whitelist_path is True:
            self.info(
                "Whitelist is empty! Use <comment>whitelist add</comment> command"
            )
        elif whitelist_path:
            self.info(
                f"The path is whitelisted through <comment>{whitelist_path}</comment>"
            )
        else:
            self.line_error(f"The path is not in whitelist!")


class WhitelistCommand(Command):
    """
    Adds the given folder(s) to whitelist.

    whitelist
    """

    commands = [
        WhitelistAddCommand(),
        WhitelistShowCommand(),
        WhitelistRemoveCommand(),
        WhitelistTestCommand(),
    ]

    def handle(self):
        return self.call("help", self._config.name)
