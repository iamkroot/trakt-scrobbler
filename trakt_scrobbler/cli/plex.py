from typing import Annotated

import typer
from rich.prompt import Prompt

from trakt_scrobbler import logger
from .console import console

app = typer.Typer(help="Runs the authentication flow for plex.")


@app.command(name="auth", help="Runs the authentication flow for Plex")
def auth(
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force run the flow, ignoring already existing credentials",
        ),
    ] = False,
    token: Annotated[
        bool,
        typer.Option(
            "--token",
            "-t",
            help="Enter plex token directly instead of password. Implies --force",
        ),
    ] = False,
):
    from trakt_scrobbler.player_monitors.plex import PlexAuth
    from trakt_scrobbler.player_monitors.plex import token as token_store

    if force or token:  # token implies force
        del token_store.data
        console.print("Forcing plex authentication")

    if token:
        # TODO: Verify that token is valid
        token_store.data = Prompt.ask("[question]Enter token[/]", console=console)
        console.print("Plex token is saved.", style="info")
    elif not token_store:
        plex_auth = PlexAuth()
        if plex_auth.device_auth():
            logger.info("Saved plex token")
            console.print("Plex token is saved.", style="info")
        else:
            console.print("Failed to retrieve plex token.", style="error")
            raise typer.Exit(1)
    else:
        console.print("Plex token is saved.", style="info")
