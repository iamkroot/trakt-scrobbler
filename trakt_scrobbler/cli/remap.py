import typer

from trakt_scrobbler.utils import pluralize

from .console import console
from .utils import add_log_handler

app = typer.Typer(help="Operations related to mediainfo remap rules.")


def print_error_details(err):
    if (
        len(err["loc"]) > 2
        and err["loc"][0] == "rules"
        and isinstance(err["loc"][1], int)
    ):
        console.print(f"For [info]rule {err['loc'][1]}[/]", style="error")
        console.print(
            f"\tIn field [info]{'.'.join(map(str, err['loc'][2:]))}[/]: [error]{err['msg']}[/]",
            style="error",
        )
    else:
        console.print(
            f"\tError at [info]{'.'.join(map(str, err['loc']))}[/]: [error]{err['msg']}[/]",
            style="error",
        )
    console.print("\tGot input: ", style="error")
    console.print(err["input"])


@app.command(help="Check for any errors in the remap_rules.toml file.")
def checkfile(
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase verbosity"
    ),
):
    from pydantic import ValidationError

    from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH, read_file

    add_log_handler(verbose, console)

    console.print(
        f"Testing remap file at [question]{REMAP_FILE_PATH}[/].", style="comment"
    )

    try:
        rules = read_file(REMAP_FILE_PATH)
    except ValidationError as e:
        console.print(
            f"Got [error]{e.error_count()}[/] validation {pluralize(e.error_count(), 'error')} for [error]{e.title}[/]",
            style="error",
        )
        for err in e.errors(include_context=False):
            print_error_details(err)
    else:
        console.print(
            f"Read {len(rules)} {pluralize(len(rules), 'rule')}. All good!",
            style="info",
        )
        if verbose >= 2:
            # TODO: Implement rich print protocol for RemapRule
            console.print(rules)
        else:
            console.print(
                "[info]Hint:[/] Try running [comment]trakts remap checkfile -vv[/]"
                " to print the parsed rules if you think something is still wrong."
            )


@app.command(name="open", help="Open the remap rules file in your default editor.")
def open_command():
    from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH
    from trakt_scrobbler.utils import open_file

    if not REMAP_FILE_PATH.exists():
        console.print(f'Remap file not found at "{REMAP_FILE_PATH}"', style="error")
        return 1
    console.print(
        f'Remap file is located at: [comment]"{REMAP_FILE_PATH}"[/comment]',
        style="info",
    )
    open_file(REMAP_FILE_PATH)
    console.print(
        "In case this command doesn't work, "
        "manually open the remap rules file from the path."
    )


@app.command(help="Prints the location of the remap location file.")
def path():
    from trakt_scrobbler.mediainfo_remap import REMAP_FILE_PATH

    console.print(f"{REMAP_FILE_PATH}")
