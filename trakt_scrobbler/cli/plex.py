from typing import Annotated

import typer
from rich.prompt import Prompt

from trakt_scrobbler import logger
from trakt_scrobbler.utils import safe_request

from .console import console

app = typer.Typer(help="Runs the authentication flow for plex.")


def plex_token_auth(login, password):
    auth_params = {
        "url": "https://plex.tv/users/sign_in.json",
        "data": {"user[login]": login, "user[password]": password},
        "headers": {
            "X-Plex-Client-Identifier": "com.iamkroot.trakt_scrobbler",
            "X-Plex-Product": "Trakt Scrobbler",
            "Accept": "application/json",
        },
    }
    return safe_request("post", auth_params)


def get_token():
    logger.info("Retrieving plex token")
    login = Prompt.ask("Plex login ID", console=console)
    pwd = Prompt.ask("Plex password", password=True, console=console)
    resp = plex_token_auth(login, pwd)
    if resp:
        return resp.json()["user"]["authToken"]
    elif resp is not None:
        err_msg = resp.json().get("error", resp.text)
        console.print(err_msg, style="error")
        logger.error(err_msg)
        return None
    else:
        logger.error("Unable to get access token")
        return None


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
    from trakt_scrobbler.player_monitors.plex import token as token_store

    if force or token:  # token implies force
        del token_store.data
        console.print("Forcing plex authentication")

    if token:
        # TODO: Verify that token is valid
        token_store.data = Prompt.ask("[question]Enter token[/]", console=console)
    elif not token_store:
        token_data = get_token()
        if token_data:
            token_store.data = token_data
            logger.info("Saved plex token")

    if token_store:
        console.print("Plex token is saved.", style="info")
    else:
        console.print("Failed to retrieve plex token.", style="error")
        raise typer.Exit(1)
