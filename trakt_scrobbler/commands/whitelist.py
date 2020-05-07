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
            self.error(f"Invalid folder {folder}")
            return
        if not fold.exists() and not self.confirm(
            f"Folder {fold} does not exist. Are you sure you want to add it?"
        ):
            return
        folder = str(fold.absolute().resolve())
        if folder.endswith("\\"):  # fix string escaping
            folder += "\\"
        self.call_sub("config set", f'--add fileinfo.whitelist "{folder}"', True)
        self.line(f"'{folder}' added to whitelist.")

    def handle(self):
        for folder in self.argument("folder"):
            self._add_single(folder)


class WhitelistShowCommand(Command):
    """
    Show the current whitelist.

    show
    """

    def handle(self):
        from trakt_scrobbler import config

        wl = config["fileinfo"]["whitelist"].get()
        self.render_table(["Whitelist:"], list(map(lambda f: [f], wl)), "compact")


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
            default=True
        ):
            self.line("Aborted", "error")
            return
        for choice in choices:
            whitelist.remove(choice)
        config["fileinfo"]["whitelist"] = whitelist

        ConfigCommand.save_config(config)

        self.call_sub("whitelist show")


class WhitelistCommand(Command):
    """
    Adds the given folder(s) to whitelist.

    whitelist
    """

    commands = [WhitelistAddCommand(), WhitelistShowCommand(), WhitelistRemoveCommand()]

    def handle(self):
        return self.call("help", self._config.name)
