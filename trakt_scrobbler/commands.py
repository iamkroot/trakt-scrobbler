#!/usr/bin/env python
from cleo import Command, Application
import sys
import subprocess as sp
from pathlib import Path

APP_NAME = "trakt-scrobbler"
platform = sys.platform


class StartCommand(Command):
    """
    Starts the trakt-scrobbler service. If already running, does nothing.

    start
        {--r|restart : Restart the service}
    """

    def handle(self):
        restart = self.option("restart")
        if platform == "linux":
            cmd = "restart" if restart else "start"
            sp.run(["systemctl", "--user", cmd, "trakt-scrobbler.service"])
        else:
            raise NotImplementedError("Only linux is supported currently")
        print("The monitors have started.")


class StopCommand(Command):
    """
    Stops the trakt-scrobbler service.

    stop
    """

    def handle(self):
        if platform == "linux":
            sp.check_call(["systemctl", "--user", "stop", "trakt-scrobbler.service"])
        else:
            raise NotImplementedError("Only linux is supported currently")
        print("The monitors are stopped.")


class StatusCommand(Command):
    """
    Shows the status trakt-scrobbler service.

    status
    """

    def handle(self):
        if platform == "linux":
            proc = sp.run(
                ["systemctl", "--user", "status", "trakt-scrobbler.service"],
                text=True,
                capture_output=True,
            )
            status = proc.stdout
        else:
            raise NotImplementedError("Only linux is supported currently")
        print(status)


class RunCommand(Command):
    """
    Run the scrobbler in the foreground.

    run
    """

    def handle(self):
        # TODO: Find a better way to run the packages
        import os
        p = Path(__file__).parent
        sys.path.append(str(p))
        os.chdir(p)
        from trakt_scrobbler.main import main
        main()


def main():
    application = Application("trakts")
    application.add(StartCommand())
    application.add(StopCommand())
    application.add(StatusCommand())
    application.add(RunCommand())
    application.run()


if __name__ == '__main__':
    main()
