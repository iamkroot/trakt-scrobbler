import os
import shutil
import subprocess as sp
from pathlib import Path
from textwrap import dedent
from .command import Command, platform, APP_NAME, CMD_NAME


def get_autostart_serv_path() -> Path:
    if platform == "darwin":
        return Path(f"~/Library/LaunchAgents/{APP_NAME}.plist").expanduser()
    elif platform == "linux":
        return Path(f"~/.config/systemd/user/{APP_NAME}.service").expanduser()
    else:
        from winreg import OpenKey, ConnectRegistry, QueryValueEx, HKEY_CURRENT_USER
        key = OpenKey(
            ConnectRegistry(None, HKEY_CURRENT_USER),
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        path = QueryValueEx(key, "Startup")[0]
        return Path(path) / (APP_NAME + ".vbs")


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
            After=default.target

            [Service]
            ExecStart="{self.cmd_path}" run
            Env="DISPLAY=:0"

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
