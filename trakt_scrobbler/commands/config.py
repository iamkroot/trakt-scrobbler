from .command import Command, CMD_NAME


class ConfigListCommand(Command):
    """
    Lists configuration settings. By default, only overriden values are shown.

    list
        {--all : Include default values too}
    """

    def _print_cfg(self, cfg: dict, prefix=""):
        for k, v in cfg.items():
            key = prefix + k
            if isinstance(v, dict):
                self._print_cfg(v, key + ".")
            else:
                self.line(f"{key} = {v}")

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

    <comment>trakts config set players.monitored mpv vlc mpc-be</comment>

For values containing space(s), surround them with double-quotes. Eg:

    <comment>trakts config set fileinfo.whitelist D:\\Media\\Movies "C:\\Users\\My Name\\Shows"</comment>

Use --add to avoid overwriting the previous list values (whitelist, monitored, etc.):

    <comment>trakts config set players.monitored mpv vlc</comment>
    <comment>trakts config set --add players.monitored plex mpc-hc</comment>

will have final value: players.monitored = ['mpv', 'vlc', 'plex', 'mpc-hc']"""

    def handle(self):
        import confuse
        from trakt_scrobbler import config

        view = config
        key = self.argument("key")
        values = self.argument("value")

        # fix path escaping due to trailing backslash for windows
        values = [val[:-1] if val.endswith(r"\\") else val for val in values]

        for name in key.split("."):
            view = view[name]

        try:
            orig_val = view.get()
            if isinstance(orig_val, dict):
                raise confuse.ConfigTypeError
        except confuse.ConfigTypeError:
            raise KeyError(f"{key} is not a valid parameter name.")
        except confuse.NotFoundError:
            value = values[0] if len(values) == 1 else values
            view.add(value)
        else:
            if not isinstance(orig_val, list):
                if len(values) > 1:
                    raise ValueError("Given parameter only accepts a single value")
                else:
                    value = orig_val.__class__(values[0])
            else:
                if self.option("add"):
                    value = list(set(orig_val).union(values))
                else:
                    value = values
            view.set(value)

        ConfigCommand.save_config(config)
        self.line(f"User config updated with '{key} = {value}'")
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
            self.line(f"{key} not found in user config.", "error")
            self.line(f"Run '{CMD_NAME} config list' to see all user-defined values.")
            return 1

        for src in temp_root.sources:
            for part in parts:
                src = src[part]
            if name in src:
                del src[name]

        ConfigCommand.save_config(config)

        self.line(f"Successfully unset {key}")


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
