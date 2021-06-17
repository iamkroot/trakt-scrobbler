from .command import Command
from trakt_scrobbler.utils import pluralize


class BacklogListCommand(Command):
    """
    List the files in backlog.

    list
    """

    def handle(self):
        from trakt_scrobbler.backlog_cleaner import BacklogCleaner
        from datetime import datetime

        backlog = BacklogCleaner(manual=True).backlog
        if not backlog:
            self.line("No items in backlog!")
            return

        episodes, movies = [], []
        for item in backlog:
            data = dict(item["media_info"])
            group = episodes if data["type"] == "episode" else movies
            del data["type"]
            data["progress"] = str(item["progress"]) + "%"
            data["watch time"] = f'{datetime.fromtimestamp(item["updated_at"]):%c}'
            group.append(data)

        if episodes:
            self.info("Episodes:")
            self.render_table(
                list(map(str.title, episodes[0].keys())),
                list(list(map(str, media.values())) for media in episodes),
                "compact",
            )

        if movies:
            if episodes:
                self.line("")
            self.info("Movies:")
            self.render_table(
                list(map(str.title, movies[0].keys())),
                list(list(map(str, media.values())) for media in movies),
                "compact",
            )


class BacklogClearCommand(Command):
    """
    Try to sync the backlog with trakt servers.

    clear
    """

    def handle(self):
        from trakt_scrobbler.backlog_cleaner import BacklogCleaner

        cleaner = BacklogCleaner(manual=True)
        if cleaner.backlog:
            old = len(cleaner.backlog)
            cleaner.clear()
            if cleaner.backlog:
                self.line(
                    "Failed to clear backlog! Check log file for information.", "error"
                )
            else:
                self.info(f"Cleared {old} {pluralize(old, 'item')}.")
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
        if cleaner.backlog:
            res = self.confirm("WARNING: This may cause loss of scrobbles. Continue?")
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
