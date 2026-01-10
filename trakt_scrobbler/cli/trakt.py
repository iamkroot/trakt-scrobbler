from typing import Annotated

import typer

from .console import console

app = typer.Typer(no_args_is_help=True)


@app.command(help="Runs the authentication flow for trakt.tv")
def auth(
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force run the flow, ignoring already existing credentials",
        ),
    ] = False,
):
    from trakt_scrobbler.trakt_auth import TraktAuth

    trakt_auth = TraktAuth()

    if force:
        console.print("Forcing trakt authentication", style="info")
        trakt_auth.clear_token()
    if not trakt_auth.get_access_token():
        console.print("Failed to retrieve trakt token.", style="error")
        return 1
    expiry_date = trakt_auth.token_expires_at().date()
    console.print(f"Token valid until {expiry_date:%x}")
