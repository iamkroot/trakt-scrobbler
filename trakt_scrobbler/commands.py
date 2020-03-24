#!/usr/bin/env python
from cleo import Command, Application
import sys
import subprocess as sp
from pathlib import Path
from textwrap import dedent
import shutil
import os

APP_NAME = "trakt-scrobbler"
CMD_NAME = "trakts"
platform = sys.platform


class StartCommand(Command):
    """
    Starts the trakt-scrobbler service. If already running, does nothing.

    start
        {--r|restart : Restart the service}
    """

    def handle(self):
        restart = self.option("restart")
        if platform == "darwin":
            if restart:
                sp.check_call(
                    ["launchctl", "kickstart", "-k", "com.iamkroot.trakt-scrobbler"]
                )
            else:
                sp.check_call(["launchctl", "start", "com.iamkroot.trakt-scrobbler"])
        if platform == "linux":
            cmd = "restart" if restart else "start"
            sp.check_call(["systemctl", "--user", cmd, "trakt-scrobbler"])
        else:
            raise NotImplementedError("Windows not supported")
        print("The monitors have started.")


class StopCommand(Command):
    """
    Stops the trakt-scrobbler service.

    stop
    """

    def handle(self):
        if platform == "darwin":
            sp.check_call(["launchctl", "stop", "com.iamkroot.trakt-scrobbler"])
        elif platform == "linux":
            sp.check_call(["systemctl", "--user", "stop", "trakt-scrobbler"])
        else:
            raise NotImplementedError("Windows not supported")
        print("The monitors are stopped.")


class StatusCommand(Command):
    """
    Shows the status trakt-scrobbler service.

    status
    """

    def handle(self):
        if platform == "darwin":
            proc = sp.run(
                ["launchctl", "list", "com.iamkroot.trakt-scrobbler"],
                text=True,
                capture_output=True,
            )
            status = proc.stdout
        elif platform == "linux":
            proc = sp.run(
                ["systemctl", "--user", "status", "trakt-scrobbler"],
                text=True,
                capture_output=True,
            )
            status = proc.stdout
        else:
            raise NotImplementedError("Windows not supported")
        print(status)


class RunCommand(Command):
    """
    Run the scrobbler in the foreground.

    run
    """

    def handle(self):
        from trakt_scrobbler.main import main

        main()


class AutostartCommand(Command):
    """
    Controls the autostart behaviour of the scrobbler

    autostart
    """

    @staticmethod
    def get_autostart_serv_path() -> Path:
        if platform == "darwin":
            return Path(f"~/Library/LaunchAgents/{APP_NAME}.plist").expanduser()
        elif platform == "linux":
            return Path(f"~/.config/systemd/user/{APP_NAME}.service").expanduser()
        else:
            return (
                Path(os.getenv("APPDATA"))
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Startup"
                / (APP_NAME + ".bat")
            )

    commands = []

    def handle(self):
        return self.call("help", self._config.name)


class AutostartEnableCommand(Command):
    """
    Installs and enables the autostart service.

    enable
    """

    def create_mac_plist(self):
        self.PLIST_LOC = AutostartCommand.get_autostart_serv_path()
        plist = dedent(
            f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
                "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>com.iamkroot.trakt-scrobbler</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{self.cmd_path}</string>
                    <string>run</string>
                </array>
                <key>RunAtLoad</key>
                <true />
                <key>LaunchOnlyOnce</key>
                <true />
                <key>KeepAlive</key>
                <true />
            </dict>
            </plist>
            """
        )
        self.PLIST_LOC.parent.mkdir(parents=True, exist_ok=True)
        self.PLIST_LOC.write_text(plist.strip())

    def create_systemd_service(self):
        self.SYSTEMD_SERV = AutostartCommand.get_autostart_serv_path()
        contents = dedent(
            f"""
            [Unit]
            Description=Trakt Scrobbler Service

            [Service]
            ExecStart="{self.cmd_path}" run

            [Install]
            WantedBy=default.target
            """
        )
        self.SYSTEMD_SERV.parent.mkdir(parents=True, exist_ok=True)
        self.SYSTEMD_SERV.write_text(contents.strip())

    def create_win_startup(self):
        self.WIN_STARTUP_SCRIPT = AutostartCommand.get_autostart_serv_path()
        contents = dedent(
            f"""
            @echo off
            start "trakt-scrobbler" /B "{self.cmd_path}" run
            """
        )

        self.WIN_STARTUP_SCRIPT.write_text(contents.strip())

    def handle(self):
        self.cmd_path = shutil.which(CMD_NAME)

        if platform == "darwin":
            self.create_mac_plist()
            sp.check_call(["launchctl", "load", "-w", str(self.PLIST_LOC)])
        elif platform == "linux":
            self.create_systemd_service()
            sp.check_call(["systemctl", "--user", "daemon-reload"])
            sp.check_call(["systemctl", "--user", "enable", "trakt-scrobbler"])
        else:
            self.create_win_startup()
        self.line(
            "Autostart Service has been enabled. "
            "The scrobbler will now run automatically when computer starts."
        )


class AutostartDisableCommand(Command):
    """
    Disables the autostart service.

    disable
    """

    def handle(self):
        if platform == "darwin":
            self.PLIST_LOC = AutostartCommand.get_autostart_serv_path()
            sp.check_call(["launchctl", "unload", "-w", str(self.PLIST_LOC)])
        elif platform == "linux":
            sp.check_call(["systemctl", "--user", "disable", "trakt-scrobbler"])
        else:
            self.WIN_STARTUP_SCRIPT = AutostartCommand.get_autostart_serv_path()
            self.WIN_STARTUP_SCRIPT.unlink()


AutostartCommand.commands.append(AutostartEnableCommand())
AutostartCommand.commands.append(AutostartDisableCommand())


class TraktAuthCommand(Command):
    """
    Runs the authetication flow for trakt.tv

    auth
        {--f|force : Force run the flow, ignoring already existing credentials.}
    """

    def handle(self):
        from trakt_scrobbler import trakt_interface as ti
        from datetime import date

        if self.option("force"):
            ti.token_data = None
            self.line("Forcing trakt authentication")
        ti.get_access_token()
        expiry = date.fromtimestamp(
            ti.token_data["created_at"] + ti.token_data["expires_in"]
        )
        self.line(f"Token valid until: {expiry}")


class ConfigCommand(Command):
    """
    Edits the scrobbler config settings.

    config
    """

    commands = []

    def handle(self):
        return self.call("help", self._config.name)


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

    help = """Separate multiple values with spaces. Eg:
    <comment>trakts config set players.monitored mpv vlc mpc-be</comment>

For values containing space(s), surround them with double-quotes. Eg:
    <comment>trakts config set fileinfo.whitelist D:\\Media\\Movies "C:\\Users\\My Name\\Shows"</comment>

Use --add to avoid overwriting the previous list values (whitelist, monitored, etc.):
    <comment>trakts config set players.monitored mpv vlc</comment>
    <comment>trakts config set --add players.monitored plex mpc-hc</comment>
will have final value: players.monitored = ['mpv', 'vlc', 'plex', 'mpc-hc']
"""

    def handle(self):
        import confuse
        from trakt_scrobbler import config

        view = config
        key = self.argument("key")
        for name in key.split("."):
            view = view[name]

        try:
            orig_val = view.get()
            if isinstance(orig_val, dict):
                raise confuse.ConfigTypeError
        except confuse.ConfigTypeError:
            raise KeyError(f"{key} is not a valid parameter name.")

        values = self.argument("value")
        if not isinstance(orig_val, list):
            if len(values) > 1:
                raise ValueError("Given parameter only accepts a single value")
            else:
                value = orig_val.__class__(values[0])
        else:
            if self.option("add"):
                value = orig_val + values
            else:
                value = values

        view.set(value)
        with open(config.user_config_path(), "w") as f:
            f.write(config.dump(full=False))
        self.line(f"User config updated with '{key} = {value}'")
        self.line("Don't forget to restart the service for the changes to take effect.")


ConfigCommand.commands.append(ConfigListCommand())
ConfigCommand.commands.append(ConfigSetCommand())


def main():
    application = Application(CMD_NAME)
    application.add(StartCommand())
    application.add(StopCommand())
    application.add(StatusCommand())
    application.add(RunCommand())
    application.add(TraktAuthCommand())
    application.add(AutostartCommand())
    application.add(ConfigCommand())
    application.run()


if __name__ == '__main__':
    main()
