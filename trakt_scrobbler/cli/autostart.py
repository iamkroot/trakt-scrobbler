import shutil
import subprocess as sp
import sys
from pathlib import Path
from textwrap import dedent

import typer

from . import APP_NAME, CMD_NAME
from .console import console

app = typer.Typer(help="Controls the autostart behaviour of the scrobbler.")
platform = sys.platform


def get_autostart_serv_path() -> Path:
    if platform == "darwin":
        return Path(f"~/Library/LaunchAgents/{APP_NAME}.plist").expanduser()
    elif platform == "linux":
        return Path(f"~/.config/systemd/user/{APP_NAME}.service").expanduser()
    else:
        from winreg import HKEY_CURRENT_USER, ConnectRegistry, OpenKey, QueryValueEx

        key = OpenKey(
            ConnectRegistry(None, HKEY_CURRENT_USER),
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        )
        path = QueryValueEx(key, "Startup")[0]
        return Path(path) / (APP_NAME + ".lnk")


@app.command(help="Installs and enables the autostart service.")
def enable():
    cmd_path = shutil.which(CMD_NAME)
    if not cmd_path:
        console.print(
            "Cannot find path to trakts command. Check your PATH.", style="error"
        )
        raise typer.Exit(1)

    if platform == "darwin":
        plist_loc = get_autostart_serv_path()
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
                    <string>{cmd_path}</string>
                    <string>run</string>
                </array>
                <key>RunAtLoad</key>
                <true />
            </dict>
            </plist>
            """
        )
        plist_loc.parent.mkdir(parents=True, exist_ok=True)
        plist_loc.write_text(plist.strip())
        sp.check_call(["launchctl", "load", "-w", str(plist_loc)])
    elif platform == "linux":
        systemd_serv = get_autostart_serv_path()
        contents = dedent(
            f"""
            [Unit]
            Description=Trakt Scrobbler Service
            After=default.target

            [Service]
            ExecStart="{cmd_path}" run
            Env="DISPLAY=:0"

            [Install]
            WantedBy=default.target
            """
        )
        systemd_serv.parent.mkdir(parents=True, exist_ok=True)
        systemd_serv.write_text(contents.strip())
        sp.check_call(["systemctl", "--user", "daemon-reload"])
        sp.check_call(["systemctl", "--user", "enable", "trakt-scrobbler"])
    else:
        win_startup_script = get_autostart_serv_path()
        try:
            import win32com.client
        except ImportError:
            win32com = None

        if win32com is not None:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(str(win_startup_script))
            shortcut.Targetpath = cmd_path
            shortcut.Arguments = "run"
            shortcut.WorkingDirectory = str(Path(cmd_path).parent)
            shortcut.WindowStyle = 7  # Minimized, hidden
            shortcut.save()
        else:
            # Fallback: create shortcut using PowerShell
            ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{str(win_startup_script)}")
$Shortcut.TargetPath = "{cmd_path}"
$Shortcut.Arguments = "run"
$Shortcut.WorkingDirectory = "{str(Path(cmd_path).parent)}"
$Shortcut.WindowStyle = 7
$Shortcut.Save()
'''
            sp.check_call(["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script.strip()])

    console.print(
        "Autostart Service has been enabled. "
        "The scrobbler will now run automatically when computer starts."
    )


@app.command(help="Disables the autostart service.")
def disable():
    if platform == "darwin":
        plist_loc = get_autostart_serv_path()
        sp.check_call(["launchctl", "unload", "-w", str(plist_loc)])
    elif platform == "linux":
        sp.check_call(["systemctl", "--user", "disable", "trakt-scrobbler"])
    else:
        get_autostart_serv_path().unlink()
    console.print("Autostart disabled.")
