import typer

from .console import console

app = typer.Typer(
    help="Access the log file, mainly for debugging purposes.", no_args_is_help=True
)


@app.command(name="open", help="Open the latest log file in your default editor.")
def open_command():
    from trakt_scrobbler.log_config import LOG_PATH
    from trakt_scrobbler.utils import open_file

    if not LOG_PATH.exists():
        console.print(f"Log file not found at {LOG_PATH!r}", style="error")
        raise typer.Exit(1)
    console.print(f"Log file is located at: {LOG_PATH!r}", style="info")
    open_file(LOG_PATH)
    console.print(
        "In case this command doesn't work, manually open the log file from the path."
    )


@app.command(name="path", help="Prints the location of the log file.")
def path():
    from trakt_scrobbler.log_config import LOG_PATH

    console.print(LOG_PATH)
