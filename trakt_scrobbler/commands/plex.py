from .command import Command


class PlexAuthCommand(Command):
    """
    Runs the authentication flow for trakt.tv

    plex
        {--f|force : Force run the flow, ignoring already existing credentials.}
    """

    def handle(self):
        from trakt_scrobbler.player_monitors import plex

        if self.option("force"):
            plex.PLEX_TOKEN_PATH.unlink(missing_ok=True)
            self.line("Forcing plex authentication")
        token = plex.get_token()
        if token:
            self.line("Plex token is saved.")
        else:
            self.line("Failed to retrieve plex token.", "error")
            return 1
