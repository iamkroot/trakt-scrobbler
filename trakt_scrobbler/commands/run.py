from .command import Command


class RunCommand(Command):
    """
    Run the scrobbler in the foreground.

    run
    """

    def handle(self):
        from trakt_scrobbler.main import main

        main()
