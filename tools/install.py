#!/usr/bin/python3
import os
import shutil
import subprocess as sp
import sys
from argparse import ArgumentParser
from pathlib import Path
from textwrap import dedent

APP_NAME = "trakt-scrobbler"
platform = sys.platform


def print_quit(*msg, status=1):
    print(*msg)
    exit(status)


def get_default_paths(source_dir=None):
    if not source_dir:
        source_dir = Path(__file__).parent.absolute()
    if source_dir.name == "tools":
        source_dir = source_dir.parent
    # check that actual code is present
    if not (source_dir / "trakt_scrobbler").exists():
        source_dir = None

    def get_path(path: str):
        return (Path(path) / APP_NAME).expanduser()

    if platform == "darwin":
        install_dir = get_path("~/Library/")
        cfg_dir = get_path("~/Library/Application Support/")
    elif platform == "linux":
        install_dir = get_path("~/.local/")
        cfg_dir = get_path("~/.config/")
    elif platform == "win32":
        install_dir = Path(os.getenv("LOCALAPPDATA")) / APP_NAME
        cfg_dir = Path(os.getenv("APPDATA")) / APP_NAME
    else:
        print_quit("Unsupported OS")

    install_dir.mkdir(exist_ok=True, parents=True)
    cfg_dir.mkdir(exist_ok=True, parents=True)

    return source_dir, install_dir, cfg_dir


def run_poetry_install(install_dir: Path):
    try:
        sp.check_call(
            ["poetry", "install", "--no-dev"],
            cwd=str(install_dir),
            shell=platform == "win32",
        )
    except (FileNotFoundError, sp.CalledProcessError):
        print_quit(
            "poetry is required for installation. Visit",
            "https://python-poetry.org/docs/#installation",
            "and run this script again after installing poetry.",
        )
    except Exception as e:
        print_quit("Error while installing venv using poetry.", str(e))


def copy_config(source_dir: Path, cfg_dir: Path):
    cfg_name = "config.toml"
    target_path = cfg_dir / cfg_name
    if target_path.exists():
        print(
            f"config.toml already exists in {target_path.parent}. "
            "Please ensure that it matches sample_config.toml, "
            "or the app may crash unexpectedly."
        )
        return
    source_path = source_dir / cfg_name
    if not source_path.exists():
        print_quit(
            f"config.toml not found in {cfg_dir} or {source_dir}. "
            "Please go through the Configuration section in README first."
        )
    else:
        print("Copying config to", target_path)
        shutil.copyfile(source_path, target_path)


def check_config(install_dir: Path):
    try:
        sp.check_call(
            ["poetry", "run", "python", "utils.py"],
            cwd=str(install_dir),
            shell=platform == "win32",
        )
    except sp.CalledProcessError:
        print_quit("Invalid config file!")


def copy_files(source_dir: Path, install_dir: Path):
    if install_dir.exists():
        shutil.rmtree(install_dir)
    shutil.copytree(source_dir / "trakt_scrobbler", install_dir)
    for file in ("pyproject.toml", "poetry.lock"):
        shutil.copyfile(source_dir / file, install_dir / file)


def default_python_ver():
    cmd = "import sys; print(sys.version_info.major)"
    ver = sp.check_output(["python", "-c", cmd], text=True)
    return int(ver)


def get_venv_python(install_dir: Path) -> Path:
    try:
        if default_python_ver() == 2:  # fix for poetry not using python3 as default
            sp.check_call(
                ["poetry", "env", "use", "python3"],
                cwd=str(install_dir),
                shell=platform == "win32",
            )
    except Exception as e:
        print_quit("Unable to use Python 3 for environment.", str(e))
    try:
        venv_path = Path(
            sp.check_output(
                ["poetry", "env", "info", "-p"],
                cwd=str(install_dir),
                text=True,
                shell=platform == "win32",
            )
        )
    except Exception as e:
        print_quit("Error while finding venv location using poetry.", str(e))
    if platform == "win32":
        python_path = venv_path / "Scripts" / "pythonw.exe"
    else:
        python_path = venv_path / "bin" / "python"
    if not python_path.exists():
        print_quit(python_path.name, "not found in", python_path.parent)
    return python_path


def create_systemd_service(work_dir: Path, python_path: Path):
    command = f'"{python_path}" main.py'
    service_path = Path("~/.config/systemd/user/trakt-scrobbler.service").expanduser()
    contents = dedent(
        f"""
        [Unit]
        Description=Trakt Scrobbler Service

        [Service]
        ExecStart={command}
        WorkingDirectory={work_dir}

        [Install]
        WantedBy=default.target
        """
    )
    service_path.parent.mkdir(parents=True, exist_ok=True)
    with open(service_path, "w") as f:
        f.write(contents.strip())
    sp.run(["systemctl", "--user", "daemon-reload"])
    sp.run(["systemctl", "--user", "enable", "trakt-scrobbler"])


def create_win_startup(work_dir: Path, python_path: Path):
    STARTUP_DIR = (
        Path(os.getenv("APPDATA"))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    contents = dedent(
        f"""
        @echo off
        start "trakt-scrobbler" /D "{work_dir}" /B "{python_path}" main.py
        """
    )
    with open(STARTUP_DIR / (APP_NAME + ".bat"), "w") as f:
        f.write(contents.strip())


def create_mac_plist(work_dir: Path, python_path: Path):
    PLIST_LOC = Path("~/Library/LaunchAgents/trakt-scrobbler.plist").expanduser()
    plist = dedent(
        f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
            "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>com.github.iamkroot.trakt-scrobbler</string>
            <key>ProgramArguments</key>
            <array>
                <string>{python_path}</string>
                <string>main.py</string>
            </array>
            <key>WorkingDirectory</key>
            <string>{work_dir}</string>
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
    PLIST_LOC.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_LOC, "w") as f:
        f.write(plist.strip())
    sp.run(["launchctl", "load", "-w", str(PLIST_LOC)])


def enable_autostart(work_dir: Path):
    python_path = get_venv_python(work_dir)
    if platform == "darwin":
        create_mac_plist(work_dir, python_path)
    elif platform == "linux":
        create_systemd_service(work_dir, python_path)
    else:
        create_win_startup(work_dir, python_path)


def perform_trakt_auth(install_dir: Path):
    trakt_cmd = "import trakt_interface; trakt_interface.get_access_token()"
    try:
        sp.check_call(
            ["poetry", "run", "python", "-c", trakt_cmd],
            cwd=str(install_dir),
            shell=platform == "win32",
        )
    except sp.CalledProcessError:
        print_quit("Error during trakt_auth.")


def install(args):
    print("Starting installation for trakt-scrobbler")
    source_dir, install_dir, cfg_dir = get_default_paths(args.source_dir)
    if not source_dir:
        print_quit(
            "Couldn't find the install files.",
            "Please ensure the entire repo is downloaded properly",
            "and that your current directory has the 'trakt_scrobbler' folder.",
        )
    print("Installing to", install_dir)
    copy_files(source_dir, install_dir)
    run_poetry_install(install_dir)
    copy_config(source_dir, cfg_dir)
    print("Validating config file at", cfg_dir)
    check_config(install_dir)
    print("Starting device authentication")
    perform_trakt_auth(install_dir)
    print("Enabling autostart")
    enable_autostart(install_dir)
    print("Setup complete")
    print("Please reboot your system to start the scrobbler")


def main():
    parser = ArgumentParser()
    parser.add_argument("-s", "--source-dir", type=Path)
    args = parser.parse_args()
    install(args)


if __name__ == "__main__":
    main()
