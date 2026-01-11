from pathlib import Path

import typer
from rich.prompt import Confirm
from urlmatch.urlmatch import BadMatchPattern, urlmatch

from trakt_scrobbler.utils import is_url

from .console import console

app = typer.Typer(help="Adds the given folder(s) to whitelist.", no_args_is_help=True)


def fmt(path: str) -> str:
    """Return a formatted version of the path"""
    return "[comment]{}[/]".format(path.strip("\\"))


def _parse_local(folder: str):
    try:
        fold = Path(folder)
    except ValueError:
        console.print(f"Invalid folder {folder}", style="error")
        return
    if not fold.exists() and not typer.confirm(
        f"Path [comment]{fold}[/] does not exist. Are you sure you want to add it?"
    ):
        return
    folder = str(fold.absolute())
    if folder.endswith("\\"):  # fix string escaping
        folder += "\\"
    return folder


def _parse_url(path: str):
    if path.endswith("/"):
        console.print(
            "Found a trailing '/' in the pattern. This is probably NOT what "
            "you want, since it will only match the exact path, and won't "
            "match any files under the path.",
            style="info",
        )
        if typer.confirm(
            "Should I add a [yellow]*[/] wildcard at the end to make"
            " it match all sub-paths?",
            default=True,
        ):
            path += "*"
    try:
        urlmatch(path, "<fake path>")
    except BadMatchPattern as e:
        e = str(e).strip("\\")
        console.print(f"Could not add {fmt(path)} as url:\n[error]{e}[/]")
        return
    return path


def _parse_single(path: str):
    if is_url(path):
        return _parse_url(path)
    else:
        return _parse_local(path)


@app.command(
    name="add",
    short_help="Add path to whitelist.",
    help="""Add path to whitelist.

The paths can either point to a local directory, or a remote url.

[yellow]Remote URL patterns[/]
For remote urls, we only support http(s) for now, and they can be of the form
    [dim cyan]https://www.example.org/path/to/directory[/]
and this will match all files under this directory. Example:
    [green]https://www.example.org/path/to/directory/Season 1/S01E03.mp4[/]

You can also specify a [yellow]*[/] to enable wildcard matching:
    [dim cyan]https://www.example.org/path/*[/]
    [dim cyan]https://*.example.org/path[/]
    [dim cyan]*://www.example.org/path[/]
will all match the url [green]https://www.example.org/path/to/directory/Season 1/S01E03.mp4[/].

Finally, we also allow http authentication fields in the url pattern:
    [dim cyan]https://username:password@example.org/path[/]
is ok (useful for some self-hosted servers).

See [yellow][link https://github.com/jessepollak/urlmatch#examples]https://github.com/jessepollak/urlmatch#examples[/][/] for more examples.

For extracting media info, we use the path portion of the url only, ignoring the domain name.
So in the above example, we use [green]path/to/directory/Season 1/S01E03.mp4[/] for figuring out the media info.
""",
)
def add(path: list[str]):
    path_str = " ".join(path)
    parsed = _parse_single(path_str)
    if parsed is None:
        raise typer.Exit(1)

    import confuse

    from trakt_scrobbler import config
    from trakt_scrobbler.cli.config import save_config

    whitelist_view = config["fileinfo"]["whitelist"]
    orig_val = whitelist_view.get(confuse.StrSeq(default=[]))
    new_val = list(set(orig_val).union([parsed]))
    whitelist_view.set(new_val)
    save_config(config)

    console.print(f"{fmt(parsed)} added to whitelist.")
    console.print(
        "Don't forget to restart the service for the changes to take effect.",
        style="info",
    )


@app.command(name="show", help="Show the current whitelist.")
def show():
    import confuse

    from trakt_scrobbler import config

    whitelist = config["fileinfo"]["whitelist"].get(confuse.StrSeq(default=[]))
    if not whitelist:
        console.print("Whitelist empty!")
        return

    whitelist = list(sorted(whitelist))
    console.print("Whitelisted paths:", style="info")
    for path in whitelist:
        console.print(path)


@app.command(name="remove", help="Remove folder(s) from whitelist (interactive).")
def remove():
    import confuse

    from trakt_scrobbler import config
    from trakt_scrobbler.cli.config import save_config
    from trakt_scrobbler.cli.utils import MultiChoicePrompt

    whitelist = config["fileinfo"]["whitelist"].get(confuse.StrSeq(default=[]))
    if not whitelist:
        console.print("Whitelist empty!")
        return
    whitelist = list(sorted(whitelist))

    choices = MultiChoicePrompt.ask(
        "Select the paths to be removed from whitelist",
        choices=whitelist,
        console=console,
    )

    paths = ", ".join(fmt(c) for c in choices)
    if not Confirm.ask(
        f"This will remove {paths} from whitelist. Continue?",
        default=True,
        console=console,
    ):
        console.print("Aborted", style="error")
        return
    for choice in choices:
        whitelist.remove(choice)
    config["fileinfo"]["whitelist"] = whitelist

    save_config(config)

    show()


@app.command(name="test", help="Check whether the given path is whitelisted.")
def test(path: str):
    from trakt_scrobbler.file_info import whitelist_file

    whitelist_path = whitelist_file(path, is_url(path), return_path=True)
    if whitelist_path is True:
        console.print(
            "Whitelist is empty, so given path is trivially whitelisted.", style="info"
        )
    elif whitelist_path:
        console.print(
            f"The path is whitelisted through {fmt(whitelist_path)}", style="info"
        )
    else:
        console.print("The path is not in whitelist!", style="error")
