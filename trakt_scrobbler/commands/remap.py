import sys
from pprint import pprint

from trakt_scrobbler.utils import pluralize
from .command import Command
import logging


class RemapCheckFileCommand(Command):
    """
    Check for any errors in the remap_rules.toml file.

    checkfile
    """

    def add_log_handler(self):
        """Output the log messages to stdout too"""
        from trakt_scrobbler import logger
        h = logging.StreamHandler()
        if self.io.is_debug():
            level = logging.DEBUG
        elif self.io.is_verbose():
            level = logging.INFO
        else:
            level = logging.WARNING
        h.setLevel(level)
        logger.addHandler(h)

    def print_error_details(self, err):
        from io import StringIO
        import textwrap
        if len(err['loc']) > 2 and err['loc'][0] == "rules" and isinstance(err['loc'][1], int):
            self.line_error(f"For <info>rule {err['loc'][1]}</>")
            self.line_error(f"\tIn field <info>{'.'.join(map(str,err['loc'][2:]))}</>: <error>{err['msg']}</>")
        else:
            self.line_error(f"\tError at <info>{'.'.join(map(str,err['loc']))}</>: <error>{err['msg']}</>")
        self.line_error("\tGot input: ")
        stream = StringIO()
        pprint(err['input'], stream=stream, compact=True, sort_dicts=False)
        self.line_error(textwrap.indent(stream.getvalue(), "\t" * 2))

    def handle(self):
        from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH, read_file
        from pydantic import ValidationError

        self.add_log_handler()

        self.comment(f"Testing remap file at <question>{REMAP_FILE_PATH}</>.")

        try:
            rules = read_file(REMAP_FILE_PATH)
        except ValidationError as e:
            self.line_error(f"Got <error>{e.error_count()}</> validation {pluralize(e.error_count(), 'error')} for <error>{e.title}</>")
            for err in e.errors(include_context=False):
                self.print_error_details(err)
        else:
            self.info(f"Read {len(rules)} {pluralize(len(rules), "rule")}. All good!")
            if self.io.is_very_verbose():
                # TODO: Colorize this with rich
                pprint(rules, stream=sys.stderr)
            else:
                self.line("<info>Hint:</> Try running <comment>trakts remap checkfile -vv</>"
                             " to print the parsed rules if you think something is still wrong.")


class RemapOpenCommand(Command):
    """
    Open the remap rules file in your default editor.

    open
    """

    def handle(self):
        from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH
        from trakt_scrobbler.utils import open_file

        if not REMAP_FILE_PATH.exists():
            self.line(f'Remap file not found at "{REMAP_FILE_PATH}"', "error")
            return 1
        self.info(f'Remap file is located at: <comment>"{REMAP_FILE_PATH}"</comment>')
        open_file(REMAP_FILE_PATH)
        self.line(
            "In case this command doesn't work, "
            "manually open the remap rules file from the path."
        )


class RemapLocationCommand(Command):
    """
    Prints the location of the remap location file.

    path
    """

    def handle(self):
        from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH

        self.line(f'{REMAP_FILE_PATH}')


class RemapCommand(Command):
    """
    Operations related to mediainfo remap rules.

    remap
    """

    commands = [
        RemapCheckFileCommand(),
        RemapLocationCommand(),
        RemapOpenCommand(),
    ]

    def handle(self):
        return self.call("help", self._config.name)
