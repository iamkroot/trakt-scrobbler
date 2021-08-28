from .command import Command, CMD_NAME


class ConfigListCommand(Command):
    """
    Lists configuration settings. By default, only overridden values are shown.

    list
        {--all : Include default values too}
    """

    def _print_cfg(self, cfg: dict, prefix=""):
        for k, v in cfg.items():
            key = prefix + k
            if isinstance(v, dict):
                self._print_cfg(v, key + ".")
            else:
                self.line(f"<info>{key}</> = <comment>{v!r}</>")

    def handle(self):
        import confuse
        from trakt_scrobbler import config

        if self.option("all"):
            self._print_cfg(config.flatten())
        else:
            sources = [s for s in config.sources if not s.default]
            temp_root = confuse.RootView(sources)
            self._print_cfg(temp_root.flatten())


class ConfigSetCommand(Command):
    """
    Set the value for a config parameter.

    set
        {key : Config parameter}
        {value* : Setting value}
        {--add : In case of list values, add them to the end instead of overwriting}
    """

    help = """Separate multiple values with spaces.

Eg:

    <question>trakts config set players.monitored mpv vlc mpc-be</>

For values containing space(s), surround them with double-quotes. Eg:

    <question>trakts config set fileinfo.whitelist D:\\Media\\Movies "C:\\Users\\My Name\\Shows"</>

Use --add to avoid overwriting the previous list values (whitelist, monitored, etc.):

    <question>trakts config set players.monitored mpv vlc</>
    <question>trakts config set --add players.monitored plex mpc-hc</>

will have final value: <info>players.monitored</> = <comment>['mpv', 'vlc', 'plex', 'mpc-hc']</>"""

    TRUTHY_BOOL = ("true", "yes", "1")

    def handle_enable_notifs(self, config, view, key, values):
        if len(values) != 1:
            raise ValueError("Given parameter only accepts a single value")
        from trakt_scrobbler.notifier import CATEGORIES

        value = values[0].lower() in self.TRUTHY_BOOL

        view = view["general"]["enable_notifs"]
        user_cat = key.replace("general.enable_notifs", "").lstrip(".")
        if user_cat:
            heirarchy = user_cat.split('.')
            categories = CATEGORIES
            for sub_category in heirarchy:  # traverse down the heirarchy
                if sub_category not in categories:
                    raise KeyError(f"<info>{sub_category}</> is not a valid category name.")
                categories = categories[sub_category]
                view = view[sub_category]
        view.set(value)

        ConfigCommand.save_config(config)
        self.line(f'User config updated with <info>{key}</> = <comment>{value!r}</>')
        self.line("Don't forget to restart the service for the changes to take effect.")

    def handle(self):
        import confuse
        from trakt_scrobbler import config

        view = config
        key = self.argument("key").strip(".")
        values = self.argument("value")

        # special case for notification categories
        if key.startswith("general.enable_notifs"):
            return self.handle_enable_notifs(config, view, key, values)

        # fix path escaping due to trailing backslash for windows
        values = [val[:-1] if val.endswith(r"\\") else val for val in values]

        for name in key.split("."):
            view = view[name]

        try:
            orig_val = view.get()
            if isinstance(orig_val, dict):
                raise confuse.ConfigTypeError
        except confuse.ConfigTypeError:
            self.line(f"Leaf key <info>{key}</> not found in user config.", "error")
            self.line(f"Run <question>{CMD_NAME} config list --all</> to see all "
                       "possible keys and their current values.")
            return 1
        except confuse.NotFoundError:
            value = values[0] if len(values) == 1 else values
            view.add(value)
        else:
            if isinstance(orig_val, list):
                if self.option("add"):
                    value = list(set(orig_val).union(values))
                else:
                    value = values
            elif len(values) == 1:
                if isinstance(orig_val, bool):
                    value = values[0].lower() in self.TRUTHY_BOOL
                else:
                    value = orig_val.__class__(values[0])
            else:
                self.line("Given parameter only accepts a single value", "error")
                return 1
            view.set(value)

        ConfigCommand.save_config(config)
        self.line(f'User config updated with <info>{key}</> = <comment>{value!r}</>')
        self.line("Don't forget to restart the service for the changes to take effect.")


class ConfigUnsetCommand(Command):
    """
    Reset a config value to its default.

    unset
        {key : Config parameter}
    """

    def handle(self):
        import confuse
        from trakt_scrobbler import config

        key = self.argument("key")
        *parts, name = key.split(".")
        sources = [s for s in config.sources if not s.default]
        temp_root = confuse.RootView(sources)
        view = temp_root
        for part in parts:
            view = view[part]
        view = view[name]
        try:
            view.get()
        except confuse.NotFoundError:
            self.line(f"<info>{key}</> not found in user config.", "error")
            self.line(f"Run <question>{CMD_NAME} config list</> to see all user-defined values.")
            return 1

        for src in temp_root.sources:
            for part in parts:
                src = src[part]
            if name in src:
                del src[name]

        ConfigCommand.save_config(config)

        self.line(f"Successfully unset <info>{key}</>")


class ConfigCommand(Command):
    """
    Edits the scrobbler config settings.

    config
    """

    commands = [ConfigListCommand(), ConfigSetCommand(), ConfigUnsetCommand()]

    @staticmethod
    def save_config(config):
        with open(config.user_config_path(), "w") as f:
            f.write(config.dump(full=False))

    def handle(self):
        return self.call("help", self._config.name)
