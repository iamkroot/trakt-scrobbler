"""
To install, winserv.py --username .\{USERNAME} --password {PASS} --startup auto install
To start, winserv.py start
"""
from pathlib import Path
import site
import sys

if sys.executable.lower().endswith("pythonservice.exe"):
    scripts_dir = Path(sys.executable).parent.parent.parent.parent / "Scripts"
else:
    scripts_dir = Path(sys.executable).parent

site_dir = scripts_dir.parent / "Lib" / "site-packages"
site.addsitedir(str(site_dir), sys.path)

import win32event
import win32serviceutil
import servicemanager
import win32service
import socket


class AutostartService(win32serviceutil.ServiceFramework):
    _svc_name_ = "trakt-scrobbler"
    _svc_display_name_ = "Trakt Scrobbler"
    _svc_description_ = "Scrobbler for trakt.tv"

    @classmethod
    def parse_command_line(cls):
        win32serviceutil.HandleCommandLine(cls)

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.proc = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.proc:
            self.proc.kill()
            self.proc = None

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        import subprocess as sp
        self.proc = sp.Popen(["trakts", "run"])
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self.proc.wait()


if __name__ == '__main__':
    AutostartService.parse_command_line()
