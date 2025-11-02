import sys

from confuse import String
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

    def handle(self):
        from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH, read_file
        from pprint import pprint
        from pydantic import ValidationError
        from io import StringIO
        import textwrap

        self.add_log_handler()

        self.comment(f"Testing remap file at <question>{REMAP_FILE_PATH}</>.")

        try:
            rules = read_file(REMAP_FILE_PATH)
        except ValidationError as e:
            self.line_error(f"Got <error>{e.error_count()}</> validation {pluralize(e.error_count(), 'error')} for <error>{e.title}</>")
            for err in e.errors(include_context=False):
                if len(err['loc']) > 2 and err['loc'][0] == "rules" and isinstance(err['loc'][1], int):
                    self.line_error(f"For <info>rule {err['loc'][1]}</>")
                    self.line_error(f"\tIn field <info>{'.'.join(map(str,err['loc'][2:]))}</>: <error>{err['msg']}</>")
                    self.line_error("\tGot input: ")
                    stream = StringIO()
                    pprint(err['input'], stream=stream, compact=True, sort_dicts=False)
                    self.line_error(textwrap.indent(stream.getvalue(), "\t" * 2))
                else:
                    self.line_error(f"\tError at <info>{'.'.join(map(str,err['loc']))}</>: <error>{err['msg']}</>")
                    self.line_error("\tGot input: ")
                    stream = StringIO()
                    pprint(err['input'], stream=stream, compact=True, sort_dicts=False)
                    self.line_error(textwrap.indent(stream.getvalue(), "\t" * 2))
        else:
            self.info(f"Read {len(rules)} {pluralize(len(rules), "rule")}. All good!")
            if self.io.is_very_verbose():
                # TODO: Colorize this with rich
                pprint(rules, stream=sys.stderr)
            else:
                self.line("<info>Hint:</> Try running <comment>trakts remap checkfile -vv</>"
                             " to print the parsed rules if you think something is still wrong.")


class RemapCommand(Command):
    """
    Operations related to mediainfo remap rules.

    remap
    """

    commands = [
        RemapCheckFileCommand()
    ]

    def handle(self):
        return self.call("help", self._config.name)
