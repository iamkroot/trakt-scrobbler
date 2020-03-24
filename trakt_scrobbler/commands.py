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
install_dir = Path(__file__).parent


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
        # TODO: Find a better way to run the packages

        sys.path.insert(0, str(install_dir))
        os.chdir(install_dir)
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
        sys.path.insert(0, str(install_dir))
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


def main():
    application = Application(CMD_NAME)
    application.add(StartCommand())
    application.add(StopCommand())
    application.add(StatusCommand())
    application.add(RunCommand())
    application.add(TraktAuthCommand())
    application.add(AutostartCommand())
    application.run()


if __name__ == '__main__':
    main()
