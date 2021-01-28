from datetime import datetime
from .command import Command
from trakt_scrobbler.utils import pluralize


def _make_table(items):
    data = {
        "movies": {},
        "shows": {}
    }
    if items["shows"]:
        rows = []
        for show in items["shows"].values():
            show_rows = []
            title = show["media_info"]["title"]
            for season, episodes in show["seasons"].items():
                for episode, ep_info in episodes.items():
                    show_rows.append([
                        "",
                        f"S{season:02}E{episode:02}",
                        f'{ep_info["progress"]:.2f}%',
                        f'{datetime.fromtimestamp(ep_info["updated_at"]):%c}'
                    ])
            show_rows[0][0] = title
            rows.extend(show_rows)

        data["shows"] = dict(headers=["Show", "Episode", "Progress", "Watch Time"],
                             rows=rows)

    if items["movies"]:
        rows = []
        for movie in items["movies"].values():
            rows.append([
                movie["media_info"]["title"],
                f'{movie["progress"]:.2f}%',
                f'{datetime.fromtimestamp(movie["updated_at"]):%c}'
            ])
        data["movies"] = dict(headers=["Name", "Progress", "Watch Time"], rows=rows)
    return data


class BacklogListCommand(Command):
    """
    List the files in backlog.

    list
    """

    def handle(self):
        from trakt_scrobbler.backlog_cleaner import BacklogCleaner

        backlog = BacklogCleaner(manual=True).backlog
        if not any(backlog.values()):
            self.line("No items in backlog!")
            return
        data = _make_table(backlog)

        if data["movies"]:
            self.info("Movies:")
            self.render_table(**data["movies"], style="borderless")

        if data["shows"]:
            if data["movies"]:
                self.line("")
            self.info("Episodes:")
            self.render_table(**data["shows"], style="borderless")


class BacklogClearCommand(Command):
    """
    Try to sync the backlog with trakt servers.

    clear
    """

    def handle(self):
        from trakt_scrobbler.backlog_cleaner import BacklogCleaner

        cleaner = BacklogCleaner(manual=True)
        if any(cleaner.backlog.values()):
            success, added, invalid = cleaner.clear()
            if not success:
                self.line(
                    "Failed to clear backlog! Check log file for information.", "error"
                )
                return 1
            if any(added.values()):
                movies = added.get("movies", 0)
                episodes = added.get("episodes", 0)
                msg = "Added "
                if movies:
                    msg += f"{pluralize(movies, 'movie')}"
                if episodes:
                    if movies:
                        msg += " and "
                    msg += f"{pluralize(episodes, 'episode')}"
                self.line(msg, "info")
            if any(invalid.values()):
                self.line("Invalid media info: ", "error")
                for category, items in invalid.items():
                    if items:
                        self.line(pluralize(len(items), category[:-1].upper()), "error")
                        self.render_table(rows=items, style="compact")
        else:
            self.info("No items in backlog!")


class BacklogPurgeCommand(Command):
    """
    Purge all entries from the backlog, without trying to sync them with trakt.

    purge
    """

    def handle(self):
        from trakt_scrobbler.backlog_cleaner import BacklogCleaner

        cleaner = BacklogCleaner(manual=True)
        if any(cleaner.backlog.values()):
            self.call_sub("backlog list")
            res = self.confirm(
                "\nDelete the items <error>without</error> scrobbling to trakt?"
            )
            if res:
                old_backlog = cleaner.purge()
                num_items = len(old_backlog)
                self.info(f"Purged {num_items} {pluralize(num_items, 'item')} from backlog.")
            else:
                self.info("Backlog is unchanged.")
        else:
            self.info("No items in backlog!")


class BacklogCommand(Command):
    """
    Manage the backlog of watched media that haven't been synced with trakt servers yet

    backlog
    """

    commands = [BacklogListCommand(), BacklogClearCommand(), BacklogPurgeCommand()]

    def handle(self):
        return self.call("help", self._config.name)
