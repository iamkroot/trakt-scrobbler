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


class LookupCommand(Command):
    """
    Performs a search for the given media title

    lookup
        {name : Search term}
        {--type=* : Type of media (show/movie)}
        {--year= : Specific year}
        {--brief : Only print trakt ID of top result}
        {--max-results=3 : Number of results to display}
    """
    MEDIA_TYPES = {"show", "movie"}

    @staticmethod
    def extract_media_info(media: dict):
        media = DefaultAttrDict(media)
        return {
            "Title": media.title,
            "Year": media.year,
            "Status": media.status and media.status.title(),
            "Overview": media.overview,
            "Trakt ID": media.ids.trakt,
            "Trakt URL": media.ids.slug and f"https://trakt.tv/shows/{media.ids.slug}",
            "IMDB URL": media.ids.imdb and f"https://imdb.com/title/{media.ids.imdb}",
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
        name = self.argument("name")
        year = self.option("year")
        media_types = set(self.option("type"))
        brief = self.option("brief")
        max_results = int(self.option("max-results"))

        extra_types = media_types.difference(self.MEDIA_TYPES)
        if extra_types:
            extra_types = tuple(map(lambda s: f"<fg=yellow>{s}</>", extra_types))
            self.line_error(f"Invalid media {pluralize(extra_types, 'type')} '{' '.join(extra_types)}'!", style="error")
            self.line(f"Must be from '<info>{'</>, <info>'.join(self.MEDIA_TYPES)}</>'")
            return 1

        res = search(name, types=media_types, year=year, extended="full")
        if not res:
            self.line("No results!", style="error")
            return
        infos = []
        for media in res:
            if media['type'] not in self.MEDIA_TYPES: 
                continue
            info = self.extract_media_info(media[media["type"]])

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
            if len(infos) == max_results:
                break

        for info in infos:
            self.print_info(info)
            self.line("")
