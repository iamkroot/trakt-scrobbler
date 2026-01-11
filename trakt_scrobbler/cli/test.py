import queue
import time

import typer

from .console import console
from .utils import add_log_handler

app = typer.Typer()


def get_monitor(name):
    import confuse

    from trakt_scrobbler import config
    from trakt_scrobbler.player_monitors import collect_monitors

    all_monitors = collect_monitors()
    monitors = {Mon.name: Mon for Mon in all_monitors if isinstance(Mon.name, str)}

    try:
        Mon = monitors[name]
    except KeyError:
        names = ", ".join(sorted(map(str, monitors)))
        console.print(
            f"Unknown monitor {name!r}. Should be one of {names}", style="error"
        )
        raise typer.Exit(1)

    templ = confuse.StrSeq(default=[])
    allowed_monitors = config["players"]["monitored"].get(templ)
    if name not in allowed_monitors:
        names = ", ".join(sorted(allowed_monitors))
        console.print(
            f"{name!r} is not in list of allowed_monitors ({names})", style="comment"
        )
        cmd = f"trakts config set --add players.monitored {name}"
        console.print(f"Hint: Use [info]{cmd}[/] to monitor it.")

    return Mon


def init_monitor(Mon, queue):
    mon = Mon(queue)
    if not mon or not mon._initialized:
        console.print(f"Could not start monitor for {Mon.name}", style="error")
        raise typer.Exit(1)
    mon.setDaemon(True)
    return mon


def wait_for_connection(mon):
    with console.status("[cyan]Trying to connect"):
        for _ in range(600):  # wait for a minute
            if mon.can_connect():
                console.print("Connected", style="green")
                break
            time.sleep(0.1)
        else:
            console.print("Timed out", style="red")
            raise typer.Exit(1)


def pretty_print_status(status):
    _, data = status
    media_info = data["media_info"]
    progress = data["progress"]
    console.print("Playing ", end="")
    console.print(media_info["title"], style="info", end="")
    if media_info["type"] == "episode":
        console.print(
            " S{season:02}E{episode:02}".format(**media_info), style="info", end=""
        )
    console.print(f" at {progress:.2f}%")


@app.command(help="Test player-monitor connection.")
def test(
    player: str,
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase verbosity"
    ),
):
    Mon = get_monitor(player)

    add_log_handler(verbose, console)

    console.print(f"Testing connection with {player}.", style="comment")
    console.print(f"Please ensure that {player} is playing some media.")

    dummy_queue = queue.Queue()
    mon = init_monitor(Mon, dummy_queue)
    wait_for_connection(mon)

    if verbose >= 1:
        console.print("Starting monitor", style="info")
    mon.start()

    try:
        with console.status("Waiting for events"):
            status = dummy_queue.get(block=True, timeout=15)
            console.print("Got info")
    except queue.Empty:
        console.print("Timed out fetching events from player", style="error")
        raise typer.Exit(1)
    else:
        pretty_print_status(status)
