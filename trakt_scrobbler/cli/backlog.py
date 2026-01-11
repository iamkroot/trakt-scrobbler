from datetime import datetime

import typer
from rich.prompt import Confirm
from rich.table import Table

from trakt_scrobbler.utils import pluralize

from .console import console

app = typer.Typer(
    help="Manage the backlog of watched media that haven't been synced with trakt servers yet.",
    no_args_is_help=True,
)


@app.command(name="list", help="List the files in backlog.")
def list_backlog():
    from trakt_scrobbler.backlog_cleaner import BacklogCleaner

    backlog = BacklogCleaner(manual=True).backlog
    if not backlog:
        console.print("No items in backlog!")
        return

    episodes, movies = [], []
    for item in backlog:
        data = dict(item["media_info"])
        group = episodes if data["type"] == "episode" else movies
        del data["type"]
        data["progress"] = str(item["progress"]) + "%"
        data["watch time"] = f"{datetime.fromtimestamp(item['updated_at']):%c}"
        group.append(data)

    if episodes:
        console.print("Episodes:", style="info")

        table = Table(box=None)

        headers = list(map(str.title, episodes[0].keys()))
        for h in headers:
            table.add_column(h)
        for media in episodes:
            table.add_row(*map(str, media.values()))
        console.print(table)

    if movies:
        if episodes:
            console.print("")
        console.print("Movies:", style="info")
        table = Table(box=None)
        headers = list(map(str.title, movies[0].keys()))
        for h in headers:
            table.add_column(h)
        for media in movies:
            table.add_row(*map(str, media.values()))
        console.print(table)


@app.command(name="clear", help="Try to sync the backlog with trakt servers.")
def clear():
    from trakt_scrobbler.backlog_cleaner import BacklogCleaner

    cleaner = BacklogCleaner(manual=True)
    if cleaner.backlog:
        old = len(cleaner.backlog)
        cleaner.clear()
        if cleaner.backlog:
            console.print(
                "Failed to clear backlog! Check log file for information.",
                style="error",
            )
        else:
            console.print(f"Cleared {old} {pluralize(old, 'item')}.", style="info")
    else:
        console.print("No items in backlog!", style="info")


@app.command(
    name="purge",
    help="Delete all entries from the backlog, without trying to sync them with trakt.",
)
def purge():
    from trakt_scrobbler.backlog_cleaner import BacklogCleaner

    cleaner = BacklogCleaner(manual=True)
    if cleaner.backlog:
        if Confirm.ask(
            "WARNING: This may cause loss of scrobbles. Continue?", console=console
        ):
            old_backlog = cleaner.purge()
            num_items = len(old_backlog)
            console.print(
                f"Purged {num_items} {pluralize(num_items, 'item')} from backlog.",
                style="info",
            )
        else:
            console.print("Backlog is left unchanged.", style="info")
    else:
        console.print("No items in backlog!", style="info")
