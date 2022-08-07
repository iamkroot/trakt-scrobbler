from .command import Command


class PauseCommand(Command):
    """Pause the scrobbler for some specified duration.

    pause
        {duration : Duration of the pause}
    """

    def handle(self):
        duration = self.argument("duration")
        # TODO: Parse duration
        duration = 120
        stopped = self.call_silent("stop")
        # self.ca

