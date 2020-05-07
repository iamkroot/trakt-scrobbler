from .command import Command


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
                self.info(f"Cleared {old} items.")
        else:
            self.info("No items in backlog!")


class BacklogCommand(Command):
    """
    Manage the backlog of watched media that haven't been synced with trakt servers yet

    backlog
    """

    commands = [BacklogListCommand(), BacklogClearCommand()]

    def handle(self):
        return self.call("help", self._config.name)
