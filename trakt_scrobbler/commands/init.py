from .command import Command


class InitCommand(Command):
    """
    Runs the initial setup of the scrobbler.

    init
    """

    def get_reqd_params(self, monitors, selected):
        import confuse

        for Mon in monitors:
            if Mon.name not in selected:
                continue
            for key, val in Mon.CONFIG_TEMPLATE.items():
                if val.default is confuse.REQUIRED:
                    yield Mon, key, val

    def handle(self):
        self.comment("This will guide you through the setup of the scrobbler.")
        self.info("If you wish to quit at any point, press Ctrl+C or Cmd+C")
        from trakt_scrobbler.player_monitors import collect_monitors

        monitors = {Mon for Mon in collect_monitors() if isinstance(Mon.name, str)}
        players = self.choice(
            "Select the players that should be monitored (separate using comma)",
            sorted(Mon.name for Mon in monitors),
            None,
            multiple=True,
        )
        self.call_sub("config set", f"players.monitored {' '.join(players)}", True)
        self.line(f"Selected: {', '.join(players)}")
        self.line("<info>If you wish to change these in the future, use</info> "
                  "<comment>trakts config set players.monitored player1 player2</comment>")

        for Mon, name, val in self.get_reqd_params(monitors, players):
            msg = f"Enter '{name}' for {Mon.name}"
            if name == "password":
                val = self.secret(
                    msg + " (keep typing, password won't be displayed on screen)"
                )
            else:
                val = self.ask(msg)
            self.call_sub("config set", f'players.{Mon.name}.{name} "{val}"', True)

        if "plex" in players:
            val = self.call("plex")
            if val:
                return val

        self.info(
            "Remember to configure your player(s) as outlined at "
            "<comment>https://github.com/iamkroot/trakt-scrobbler/wiki/Players-Setup</comment>"
        )

        val = self.call("auth")
        if val:
            return val

        if self.confirm(
            "Do you wish to set the whitelist of folders to be monitored? "
            "(recommended to be set to the roots of your media directories, "
            "such as Movies folder, TV Shows folder, etc.)",
            True,
        ):
            msg = "Enter path to directory (or leave blank to continue):"
            folder = self.ask(msg)
            while folder:
                if folder.endswith("\\"):  # fix escaping
                    folder += "\\"
                self.call_sub("whitelist add", f'"{folder}"')
                folder = self.ask(msg)

        if self.confirm("Enable autostart service for scrobbler?", True):
            val = self.call_sub("autostart enable")
            if val:
                return val

        if self.confirm("Start scrobbler service now?", True):
            self.call("start")
