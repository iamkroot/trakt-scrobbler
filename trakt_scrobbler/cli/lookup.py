from typing import Annotated

import typer
from rich.table import Table

from trakt_scrobbler.utils import pluralize

from .console import console

app = typer.Typer()
MEDIA_TYPES = {"show", "movie"}


class DefaultAttrDict(dict):
    """A `dict` subclass that can be accessed via attributes (dot notation).
    Non-existent accesses return an empty dict.
    """

    def __getattr__(self, key):
        if key in self:
            val = self[key]
            if isinstance(val, dict):
                return self.__class__(val)
            else:
                return val
        else:
            return self.__class__()

    def __setattr__(self, key, value):
        self[key] = value


def extract_media_info(media: dict):
    type_ = media["type"]
    info = DefaultAttrDict(media[type_])
    return {
        "Title": info.title,
        "Year": info.year,
        "Status": info.status and info.status.title(),
        "Overview": info.overview,
        "Trakt ID": info.ids.trakt,
        "Trakt URL": info.ids.slug and f"https://trakt.tv/{type_}s/{info.ids.slug}",
        "IMDB URL": info.ids.imdb and f"https://imdb.com/title/{info.ids.imdb}",
    }


def print_info(info: dict):
    table = Table(box=None, show_header=False, pad_edge=False)
    table.add_column("Key", justify="right")
    table.add_column("Value")

    for k, v in info.items():
        style = "default"
        if "URL" in k:
            style = f"comment][link {v}"
        elif "ID" in k:
            style = "magenta"
        elif k == "MatchScore":
            if v > 900:
                style = "info"
            elif v < 300:
                style = "error"
                v = f"{v} (Warning! Very low score! Check your search query)"
        elif k == "Title":
            style = "yellow"
        if not v:
            style = "error"
            v = "Not available"

        table.add_row(f"[info]{k}[/]", f"[{style}]{v}[/]")

    console.print(table)


@app.command(help="Performs a search for the given media title.")
def lookup(
    ctx: typer.Context,
    name: Annotated[list[str], typer.Argument(help="Search term")],
    type: Annotated[
        list[str] | None, typer.Option(help="Type of media (show/movie)")
    ] = None,
    year: Annotated[str | None, typer.Option(help="Specific year")] = None,
    brief: Annotated[
        bool, typer.Option(help="Only print trakt ID of top result")
    ] = False,
    limit: Annotated[int, typer.Option(help="Number of results to fetch per page")] = 3,
    page: Annotated[int, typer.Option(help="Number of page of results to fetch")] = 1,
):
    if ctx.invoked_subcommand is not None:
        return

    from trakt_scrobbler.trakt_interface import search

    search_name = " ".join(name)
    media_types = set(type) if type else set()

    for t in media_types:
        if t not in MEDIA_TYPES:
            console.print(f"Invalid media type '{t}'!", style="error")
            console.print(
                f"Must be from '{', '.join(f'[info]{t}[/]' for t in MEDIA_TYPES)}'"
            )
            raise typer.Exit(1)

    assert limit >= 1, "Invalid limit"
    assert page >= 1, "Invalid page"

    if limit > 10:
        console.print(
            "At most 10 results can be fetched in a page. "
            "If more are required, use the --page to specify next page",
            style="info",
        )
        limit = 10

    extra_types = media_types.difference(MEDIA_TYPES)
    if extra_types:
        extra_types_str = " ".join(f"[yellow]{t}[/]" for t in extra_types)
        console.print(
            f"Invalid media {pluralize(extra_types, 'type')} '{extra_types_str}'!",
            style="error",
        )
        console.print(
            f"Must be from '{', '.join(f'[info]{t}[/]' for t in MEDIA_TYPES)}'"
        )
        raise typer.Exit(1)
    if not media_types:
        media_types = MEDIA_TYPES

    res = search(
        search_name,
        types=media_types,
        year=year,
        extended="full",
        page=page,
        limit=limit,
    )
    if not res:
        console.print("No results!", style="error")
        return
    infos = []
    for media in res:
        info = extract_media_info(media)

        if brief:
            console.print(info["Trakt ID"], style="default")
            return

        info2 = dict(
            Title=info.pop("Title"),
            Year=info.pop("Year"),
            Type=media["type"].title(),
            MatchScore=media["score"],
            **info,
        )
        infos.append(info2)
        if len(infos) == limit:
            break

    for info in infos:
        print_info(info)
        console.print("")

    console.print(
        "There may be more results available. "
        f"Add [comment]--page={page + 1}[/] to the command to see them."
    )
