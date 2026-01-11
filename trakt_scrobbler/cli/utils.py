import logging

from rich.logging import RichHandler
from rich.prompt import InvalidResponse, PromptBase
from rich.text import Text


class MultiChoicePrompt(PromptBase[list[str]]):
    """Multiple selections using a numbered list."""

    validate_error_message = (
        "[prompt.invalid]Please enter a comma-separated list of integers[/]"
    )
    prompt_suffix = "\n > "

    def make_prompt(self, default) -> Text:
        # FIXME: Support default
        assert self.choices is not None, "No choices provided"
        prompt = self.prompt.copy()
        prompt.end = ""
        for i, c in enumerate(self.choices):
            prompt.append("\n [")
            prompt.append(str(i), "cyan")
            prompt.append("] ")
            prompt.append(c, "prompt.choices")
        prompt.append(self.prompt_suffix)
        return prompt

    def response_type(self, value: str) -> list[str]:
        assert self.choices is not None, "No choices provided"
        res = []
        for v in value.split(","):
            try:
                i = int(v.strip())
            except ValueError as e:
                try:
                    # let user type the exact value.
                    assert self.case_sensitive, "FIXME: Doesn't respect case_sensitive"
                    i = self.choices.index(v.strip())
                except ValueError:
                    raise InvalidResponse(
                        f"[red]Please enter a number or comma-separated names![/] {e}"
                    )
            try:
                res.append(self.choices[i])
            except IndexError:
                raise InvalidResponse(self.illegal_choice_message + f"[/]: Got {i}")
        return res

    def process_response(self, value: str) -> list[str]:
        return self.response_type(value)


def _get_win_pid():
    import re
    import subprocess as sp

    from . import CMD_NAME

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
                "gwmi -Query \"select processid from win32_process where name='trakts.exe' and commandline like '%run%'\"",
            ],
            text=True,
        )
        pattern = re.compile(r"ProcessId\s*:\s*(?P<pid>\d+)")
    for line in op.split("\n"):
        match = pattern.search(line)
        if match:
            return match["pid"]


def _kill_task_win(pid):
    import subprocess as sp

    sp.check_call(["taskkill", "/pid", pid, "/f", "/t"])


def add_log_handler(verbose: int, console):
    """Output the log messages to stdout too"""
    from trakt_scrobbler import logger

    if verbose >= 3:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING
    h = RichHandler(level=level, console=console)
    logger.addHandler(h)
