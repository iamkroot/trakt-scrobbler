"""
This file contains monitors for players that essentially wrap over MPV.
In most cases, only the read_player_cfg method has to be overridden.
"""

import os
import re
import sys
from configparser import ConfigParser
from itertools import product
from pathlib import Path

import appdirs
from trakt_scrobbler.player_monitors.mpv import MPVMon, MPVPosixMon, MPVWinMon
from trakt_scrobbler.utils import AutoloadError

ARG_PAT = re.compile(r'--input-ipc-server=(?P<ipc_path>[^\'" ]+)')


class SMPlayerMPVMon(MPVMon):
    name = "smplayer@mpv"

    @classmethod
    def read_player_cfg(cls, auto_keys=None):
        if sys.platform == "win32":
            conf_path = Path.home() / ".smplayer" / "smplayer.ini"
        else:
            conf_path = (
                Path(appdirs.user_config_dir("smplayer", roaming=True, appauthor=False))
                / "smplayer.ini"
            )
        mpv_conf = ConfigParser(allow_no_value=True, strict=False)
        mpv_conf.optionxform = lambda option: option
        mpv_conf.read_string(conf_path.read_text(encoding="utf-8"))

        def read_ipc():
            opts = mpv_conf.get("advanced", "mplayer_additional_options")
            match = ARG_PAT.search(opts)
            if match:
                return match["ipc_path"]
            else:
                raise AutoloadError("ipc_path", conf_path, "IPC Path not specified")

        return {
            "ipc_path": read_ipc
        }


class SMPlayerMPVPosixMon(MPVPosixMon, SMPlayerMPVMon):
    pass


class SMPlayerMPVWinMon(MPVWinMon, SMPlayerMPVMon):
    pass


class SyncplayMPVMon(MPVMon):
    name = "syncplay@mpv"

    @classmethod
    def read_player_cfg(cls, auto_keys=None):
        file_names = ["syncplay.ini", ".syncplay"]
        if sys.platform == "win32":
            paths = (Path(appdirs.user_data_dir(roaming=True)),
                     Path(appdirs.user_data_dir()),)
        else:
            paths = (Path(os.getenv('XDG_CONFIG_HOME', "~/.config")).expanduser(),
                     Path.home())

        conf_paths = tuple(path / name for path, name in product(paths, file_names))
        syncplay_conf = ConfigParser(allow_no_value=True, strict=False)
        syncplay_conf.optionxform = lambda option: option
        if not syncplay_conf.read(conf_paths, encoding="utf-8-sig"):
            raise FileNotFoundError("", "", conf_paths)

        def read_ipc():
            opts = syncplay_conf.get("client_settings", "perplayerarguments")
            match = ARG_PAT.search(opts)
            if match:
                return match["ipc_path"]
            else:
                raise AutoloadError("ipc_path", conf_paths, "IPC Path not specified")

        return {
            "ipc_path": read_ipc
        }


class SyncplayMPVPosixMon(MPVPosixMon, SyncplayMPVMon):
    pass


class SyncplayMPVWinMon(MPVWinMon, SyncplayMPVMon):
    pass
