#!/usr/bin/env python
import os
import re
import shutil
import subprocess as sp
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from cleo import Application
from cleo import Command as BaseCommand
from clikit.args import StringArgs
from clikit.io import NullIO

APP_NAME = "trakt-scrobbler"
CMD_NAME = "trakts"
platform = sys.platform


class Command(BaseCommand):
    def call_sub(self, name, args="", silent=False):
        """call() equivalent which supports subcommands"""
        names = name.split(" ")
        command = self.application.get_command(names[0])
        for name in names[1:]:
            command = command.get_sub_command(name)
        args = StringArgs(args)

        return command.run(args, silent and NullIO() or self.io)


def _get_win_pid():
    op = sp.check_output(
        [
            "wmic",
            "process",
            "where",
            f"name='{CMD_NAME}.exe'",
            "get",
            "CommandLine,ProcessID",
        ],
        text=True,
    )
    for line in op.split("\n"):
        match = re.search(r" run.*?(?P<pid>\d+)", line)
        if match:
            return match["pid"]


def _kill_task_win(pid):
    sp.check_call(["taskkill", "/pid", pid, "/f"])


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
        elif platform == "linux":
            cmd = "restart" if restart else "start"
            sp.check_call(["systemctl", "--user", cmd, "trakt-scrobbler"])
        else:
            pid = _get_win_pid()
            if pid and restart:
                _kill_task_win(pid)
                pid = None
            if not pid:
                sp.check_call(
                    f'start "trakt-scrobbler" /B "{shutil.which(CMD_NAME)}" run',
                    shell=True,
                )
        self.line("The monitors are running.")


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
            pid = _get_win_pid()
            if pid:
                _kill_task_win(pid)
        self.line("The monitors are stopped.")


class StatusCommand(Command):
    """
    Shows the status trakt-scrobbler service.

    status
    """

    def check_running(self):
        is_inactive = False
        if platform == "darwin":
            output = sp.check_output(
                ["launchctl", "list", "com.iamkroot.trakt-scrobbler"], text=True,
            ).split("\n")
            for line in output:
                if "trakt-scrobbler" in line:
                    is_inactive = line.strip().startswith("-")
                    break
        elif platform == "linux":
            is_inactive = bool(
                sp.call(
                    ["systemctl", "--user", "is-active", "--quiet", "trakt-scrobbler"]
                )
            )
        else:
            is_inactive = _get_win_pid() is None
        self.line(f"The scrobbler is {'not ' * is_inactive}running")

    def get_last_action(self):
        def read_log_files():
            """Returns all lines in log files, most recent first"""
            from trakt_scrobbler.app_dirs import DATA_DIR

            log_file = DATA_DIR / "trakt_scrobbler.log"
            for file in (
                log_file,
                *(log_file.with_suffix(f".log.{i}") for i in range(1, 6)),
            ):
                if not file.exists():
                    return
                for line in reversed(file.read_text().split("\n")):
                    yield line

        PAT = re.compile(
            r"(?P<asctime>.*?) -.*Scrobble (?P<verb>\w+) successful for (?P<name>.*)"
        )

        for line in read_log_files():
            match = PAT.match(line)
            if match:
                time = datetime.strptime(match["asctime"], "%Y-%m-%d %H:%M:%S,%f")
                self.line(
                    "Last successful scrobble: {verb} {name}, at {time:%c}".format(
                        time=time, verb=match["verb"].title(), name=match["name"]
                    )
                )
                break
        else:
            self.line("No activity yet.")

    def handle(self):
        self.check_running()

        from trakt_scrobbler import config

        monitored = config['players']['monitored'].get()
        self.line(f"Monitored players: {', '.join(monitored)}")

        self.get_last_action()


class RunCommand(Command):
    """
    Run the scrobbler in the foreground.

    run
    """

    def handle(self):
        from trakt_scrobbler.main import main

        main()


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
            / (APP_NAME + ".vbs")
        )


class AutostartEnableCommand(Command):
    """
    Installs and enables the autostart service.

    enable
    """

    def create_mac_plist(self):
        self.PLIST_LOC = get_autostart_serv_path()
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
        self.SYSTEMD_SERV = get_autostart_serv_path()
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
        self.WIN_STARTUP_SCRIPT = get_autostart_serv_path()
        contents = f'CreateObject("Wscript.Shell").Run "{CMD_NAME} run", 0, False'
        self.WIN_STARTUP_SCRIPT.write_text(contents.strip())

    def handle(self):
        self.cmd_path = shutil.which(CMD_NAME)
        if not self.cmd_path:
            self.line("Cannot find path to trakts command. Check your PATH.", "error")
            return 1
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
            self.PLIST_LOC = get_autostart_serv_path()
            sp.check_call(["launchctl", "unload", "-w", str(self.PLIST_LOC)])
        elif platform == "linux":
            sp.check_call(["systemctl", "--user", "disable", "trakt-scrobbler"])
        else:
            get_autostart_serv_path().unlink()
        self.line("Autostart disabled.")


class AutostartCommand(Command):
    """
    Controls the autostart behaviour of the scrobbler

    autostart
    """

    commands = [AutostartEnableCommand(), AutostartDisableCommand()]

    def handle(self):
        return self.call("help", self._config.name)


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
        if not ti.get_access_token():
            self.line("Failed to retrieve trakt token.", "error")
            return 1
        expiry = date.fromtimestamp(
            ti.token_data["created_at"] + ti.token_data["expires_in"]
        )
        self.line(f"Token valid until: {expiry}")


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
        values = self.argument("value")
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
        with open(config.user_config_path(), "w") as f:
            f.write(config.dump(full=False))
        self.line(f"User config updated with '{key} = {value}'")
        self.line("Don't forget to restart the service for the changes to take effect.")


class ConfigCommand(Command):
    """
    Edits the scrobbler config settings.

    config
    """

    commands = [ConfigListCommand(), ConfigSetCommand()]

    def handle(self):
        return self.call("help", self._config.name)


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
        self.line(f"Selected: {', '.join(players)}")
        self.call_sub("config set", f"players.monitored {' '.join(players)}", True)

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
            "<comment>https://github.com/iamkroot/trakt-scrobbler#players</comment>"
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
                self.call_sub("whitelist", f'"{folder}"')
                folder = self.ask(msg)

        if self.confirm("Enable autostart service for scrobbler?", True):
            val = self.call_sub("autostart enable")
            if val:
                return val

        if self.confirm("Start scrobbler service now?", True):
            self.call("start")


class WhitelistShowCommand(Command):
    """
    Show the current whitelist.

    show
    """

    def handle(self):
        from trakt_scrobbler import config

        wl = config["fileinfo"]["whitelist"].get()
        self.render_table(["Whitelist:"], list(map(lambda f: [f], wl)), "compact")


class WhitelistCommand(Command):
    """
    Adds the given folder(s) to whitelist.

    whitelist
        {folder?* : Folder to be whitelisted}
    """

    commands = [WhitelistShowCommand()]

    def _add_single(self, folder: str):
        try:
            fold = Path(folder)
        except ValueError:
            self.error(f"Invalid folder {folder}")
            return
        if not fold.exists():
            if not self.confirm(
                f"Folder {fold} does not exist. Are you sure you want to add it?"
            ):
                return
        else:
            folder = str(fold.absolute().resolve())
        self.call_sub("config set", f'--add fileinfo.whitelist "{folder}"', True)
        self.line(f"'{folder}' added to whitelist.")

    def handle(self):
        for folder in self.argument("folder"):
            self._add_single(folder)


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


class PlexAuthCommand(Command):
    """
    Runs the authetication flow for trakt.tv

    plex
        {--f|force : Force run the flow, ignoring already existing credentials.}
    """

    def handle(self):
        from trakt_scrobbler.player_monitors import plex

        if self.option("force"):
            plex.token_data = None
            self.line("Forcing plex authentication")
        token = plex.get_token()
        if token:
            self.line("Plex token is saved.")
        else:
            self.line("Failed to retrieve plex token.", "error")
            return 1


class OpenLogCommand(Command):
    """
    Open the latest log file in your default editor.

    open
    """

    def handle(self):
        from trakt_scrobbler.app_dirs import DATA_DIR
        file_path = DATA_DIR / "trakt_scrobbler.log"

        if not file_path.exists():
            self.line(f'Log file not found at "{file_path}"', "error")
            return 1
        if platform == "darwin":
            sp.Popen(["open", file_path])
        elif platform == "linux":
            sp.Popen(["xdg-open", file_path])
        elif platform == "win32":
            sp.Popen(f'start "{file_path}"', shell=True)


class LogLocationCommand(Command):
    """
    Prints the location of the log file.

    path
    """

    def handle(self):
        from trakt_scrobbler.app_dirs import DATA_DIR
        file_path = DATA_DIR / "trakt_scrobbler.log"
        self.line(f'"{file_path}"')


class LogCommand(Command):
    """
    Access the log file, mainly for debugging purposes.

    log
    """
    commands = [LogLocationCommand(), OpenLogCommand()]

    def handle(self):
        return self.call("help", self._config.name)


def main():
    application = Application(CMD_NAME)
    application.add(AutostartCommand())
    application.add(BacklogCommand())
    application.add(ConfigCommand())
    application.add(InitCommand())
    application.add(LogCommand())
    application.add(PlexAuthCommand())
    application.add(RunCommand())
    application.add(StartCommand())
    application.add(StatusCommand())
    application.add(StopCommand())
    application.add(TraktAuthCommand())
    application.add(WhitelistCommand())
    application.run()


if __name__ == '__main__':
    main()
