"""
This file contains monitors for players that essentially wrap over MPV.
In most cases, only the read_player_cfg method has to be overridden.
"""

import re
import sys
from configparser import ConfigParser
from pathlib import Path

import appdirs
from trakt_scrobbler.player_monitors.mpv import MPVMon, MPVPosixMon, MPVWinMon
from trakt_scrobbler.utils import AutoloadError

ARG_PAT = re.compile(r'--input-ipc-server=(?P<ipc_path>[^" ]+)')


class SMPlayerMon(MPVMon):
    name = "smplayer"

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
        mpv_conf.read_string(conf_path.read_text())

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


class SMPlayerPosixMon(MPVPosixMon, SMPlayerMon):
    pass


class SMPlayerWinMon(MPVWinMon, SMPlayerMon):
    pass
