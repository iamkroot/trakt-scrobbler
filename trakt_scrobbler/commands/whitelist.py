from pathlib import Path

from trakt_scrobbler.utils import is_url
from urlmatch.urlmatch import BadMatchPattern, urlmatch

from .command import Command
from .config import ConfigCommand


class WhitelistAddCommand(Command):
    """
    Add path to whitelist.

    add
        {path* : path to be whitelisted}
    """

    help = """The paths can either point to a local directory, or a remote url.

<fg=yellow>Remote URL patterns</>
For remote urls, we only support http(s) for now, and they can be of the form
    <info>https://www.example.org/path/to/directory/</>
and this will match all files under this directory. Example:
    <comment>https://www.example.org/path/to/directory/Season 1/S01E03.mp4</>

You can also specify a <fg=yellow>*</> to enable wildcard matching:
    <info>https://*.example.org/path/</>
    <info>*://www.example.org/path/</>
    <info>https://*.example.org/*</>
will all match the url <comment>https://www.example.org/path/to/directory/Season 1/S01E03.mp4</>

Finally, we also allow http authentication fields in the url pattern:
    <info>https://username:password@example.org/path/</>
is ok (useful for some self-hosted servers).

See <question>https://github.com/jessepollak/urlmatch#examples</> for more examples.

For extracting media info, we use the path portion of the url only, ignoring the domain name.
So in the above example, we use <comment>path/to/directory/Season 1/S01E03.mp4</> for figuring out the media info."""

    def _parse_local(self, folder: str):
        try:
            fold = Path(folder)
        except ValueError:
            self.line_error(f"Invalid folder {folder}")
            return
        if not fold.exists() and not self.confirm(
            f"Path <comment>{fold}</> does not exist. Are you sure you want to add it?"
        ):
            return
        folder = str(fold.absolute().resolve())
        if folder.endswith("\\"):  # fix string escaping
            folder += "\\"
        return folder

    def _parse_url(self, path: str):
        try:
            urlmatch(path, "<fake path>")
        except BadMatchPattern as e:
            self.line_error(f"Could not add <comment>{path}</> as url:\n<error>{e}</>")
            return
        return path
        

    def _parse_single(self, path: str):
        if is_url(path):
            return self._parse_url(path)
        else:
            return self._parse_local(path)

    def handle(self):
        path = " ".join(self.argument("path"))
        parsed = self._parse_single(path)
        if parsed is None:
            return
        self.call_sub("config set", f'--add fileinfo.whitelist "{parsed}"', silent=True)
        self.line(f"<comment>{path}</> added to whitelist.")
        self.info("Don't forget to restart the service for the changes to take effect.")


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

        whitelist = list(sorted(whitelist))
        self.info("Whitelisted paths:")
        for path in whitelist:
            self.line(path)


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
        whitelist = list(sorted(whitelist))

        choices = self.choice(
            "Select the paths to be removed from whitelist", whitelist, multiple=True
        )
        if not self.confirm(
            f"This will remove {', '.join(f'<comment>{c}</>' for c in choices)} from whitelist. Continue?",
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
    Check whether the given path is whitelisted.

    test
        {path : path to be tested}
    """

    def handle(self):
        from trakt_scrobbler.file_info import whitelist_file

        path = self.argument("path")
        whitelist_path = whitelist_file(path, is_url(path), return_path=True)
        if whitelist_path is True:
            self.info("Whitelist is empty, so given path is trivially whitelisted.")
        elif whitelist_path:
            self.info(f"The path is whitelisted through <comment>{whitelist_path}</>")
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
