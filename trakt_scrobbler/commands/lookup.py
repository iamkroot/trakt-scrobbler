from copy import deepcopy
from trakt_scrobbler.utils import pluralize
from clikit.ui.style.table_style import TableStyle
from clikit.ui.components.table import Table
from clikit.ui.style.alignment import Alignment
from .command import Command


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


def wrap_iter(collection, style):
    return (f"<{style}>{item}</>" for item in collection)


class LookupCommand(Command):
    """
    Performs a search for the given media title

    lookup
        {name* : Search term}
        {--type=* : Type of media (show/movie)}
        {--year= : Specific year}
        {--brief : Only print trakt ID of top result}
        {--limit=3 : Number of results to fetch per page}
        {--page=1 : Number of page of results to fetch}
    """
    MEDIA_TYPES = {"show", "movie"}

    @staticmethod
    def extract_media_info(media: dict):
        type_ = media['type']
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

    def print_info(self, info: dict):
        rows = []
        for k, v in info.items():
            style = "fg=default"
            if "URL" in k:
                style = "comment"
            elif "ID" in k:
                style = "fg=magenta"
            elif k == "MatchScore":
                if v > 900:
                    style = "info"
                elif v < 300:
                    style = "error"
                    v = f"{v} (Warning! Very low score! Check your search query)"
            elif k == "Title":
                style = "fg=yellow"
            if not v:
                style = "error"
                v = "Not available"
            rows.append((f"<info>{k}</>",f"<{style}>{v}</>"))
        table_style = deepcopy(TableStyle.borderless())
        table_style.set_column_alignment(0, Alignment.RIGHT)
        table = Table(table_style)
        table.set_rows(rows)
        table.render(self._io)

    def handle(self):
        from trakt_scrobbler.trakt_interface import search
        name = " ".join(self.argument("name"))
        year = self.option("year")
        media_types = set(self.option("type"))
        brief = self.option("brief")
        limit = int(self.option("limit"))
        page = int(self.option("page"))

        assert limit >= 1, "Invalid limit"
        assert page >= 1, "Invalid page"

        if limit > 10:
            self.info("At most 10 results can be fetched in a page. "
                      "If more are required, use the --page to specify next page")
            limit = 10

        extra_types = media_types.difference(self.MEDIA_TYPES)
        if extra_types:
            extra_types = tuple(f"<fg=yellow>{t}</>" for t in extra_types)
            self.line_error(f"Invalid media {pluralize(extra_types, 'type')} '"
                            f"{' '.join(extra_types)}'!", style="error")
            self.line(f"Must be from '"
                      f"{', '.join(f'<info>{t}</>' for t in self.MEDIA_TYPES)}'")
            return 1
        if not media_types:
            media_types = self.MEDIA_TYPES

        res = search(name, types=media_types, year=year, extended="full",
                     page=page, limit=limit)
        if not res:
            self.line("No results!", style="error")
            return
        infos = []
        for media in res:
            info = self.extract_media_info(media)

            if brief:
                self.line(info["Trakt ID"], style="fg=default")
                return

            info2 = dict(
                Title=info.pop("Title"),
                Year=info.pop("Year"),
                Type=media["type"].title(),
                MatchScore=media["score"],
                **info
            )
            infos.append(info2)
            if len(infos) == limit:
                break

        for info in infos:
            self.print_info(info)
            self.line("")

        self.line("There may be more results available. "
                  f"Add <comment>--page={page+1}</> to the command to see them.")
