from .command import Command


class TraktAuthCommand(Command):
    """
    Runs the authentication flow for trakt.tv

    auth
        {--f|force : Force run the flow, ignoring already existing credentials.}
    """

    def handle(self):
        from trakt_scrobbler.trakt_auth import TraktAuth

        trakt_auth = TraktAuth()

        if self.option("force"):
            self.line("Forcing trakt authentication")
            trakt_auth.clear_token()
        if not trakt_auth.get_access_token():
            self.line("Failed to retrieve trakt token.", "error")
            return 1
        expiry_date = trakt_auth.token_expires_at().date()
        self.line(f"Token valid until {expiry_date:%x}")
