import typer
from rich.prompt import Confirm, Prompt

from .console import console
from .utils import MultiChoicePrompt

app = typer.Typer(help="Runs the initial setup of the scrobbler.")


@app.command()
def init():
    from trakt_scrobbler.player_monitors import collect_monitors

    console.print(
        "This will guide you through the setup of the scrobbler.", style="comment"
    )
    console.print(
        "If you wish to quit at any point, press Ctrl+C or Cmd+C", style="info"
    )

    monitors = {Mon for Mon in collect_monitors() if isinstance(Mon.name, str)}
    players = MultiChoicePrompt.ask(
        "Select the players that should be monitored (separate using comma)",
        choices=sorted(Mon.name for Mon in monitors),
        console=console,
    )
    from trakt_scrobbler.cli import config

    if retval := config.set_("players.monitored", players):
        return retval
    console.print(f"Selected: {', '.join(players)}")
    console.print(
        "[info]If you wish to change these in the future, use[/] "
        "[comment]trakts config set players.monitored player1 player2[/]"
    )

    for Mon, name, _ in get_reqd_params(monitors, players):
        msg = f"Enter '{name}' for {Mon.name}"
        if name == "password":
            res = Prompt.ask(
                msg + " [cyan](keep typing, password won't be displayed on screen)",
                password=True,
            )
        else:
            res = Prompt.ask(msg)
        if retval := config.set_(f"players.{Mon.name}.{name}", [res]):
            return retval

    if "plex" in players:
        # from trakt_scrobbler.cli import plex
        # if retval := plex.auth():
        #     return retval
        pass
    SETUP_URL = "https://github.com/iamkroot/trakt-scrobbler/wiki/Players-Setup"
    console.print(
        "[info]Remember to configure your player(s) as outlined at[/] "
        f"[link {SETUP_URL}]{SETUP_URL}[/]",
    )

    from trakt_scrobbler.cli import trakt

    if retval := trakt.auth():
        return retval

    if Confirm.ask(
        "[question]Do you wish to set the whitelist of folders to be monitored? "
        "[info](recommended to be set to the roots of your media directories, "
        "such as Movies folder, TV Shows folder, etc.)",
        default=True,
        console=console,
    ):
        msg = "Enter path to directory [dim](or leave blank to continue)[/]"
        folder = Prompt.ask(msg, console=console)
        while folder:
            if folder.endswith("\\"):  # fix escaping
                folder += "\\"
            # self.call_sub("whitelist add", f'"{folder}"')
            folder = Prompt.ask(msg, console=console)
    if Confirm.ask(
        "[question]Enable autostart service for scrobbler?",
        default=True,
        console=console,
    ):
        # from trakt_scrobbler.cli import autostart
        #
        # if retval := autostart.enable():
        #    return retval
        pass

    if Confirm.ask(
        "[question]Start scrobbler service now?", default=True, console=console
    ):
        # from trakt_scrobbler.cli import start
        # return start.start()
        pass


def get_reqd_params(monitors, selected):
    import confuse

    for Mon in monitors:
        if Mon.name not in selected:
            continue
        for key, val in Mon.CONFIG_TEMPLATE.items():
            if val.default is confuse.REQUIRED:
                yield Mon, key, val
