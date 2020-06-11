from .command import Command


class TraktAuthCommand(Command):
    """
    Runs the authetication flow for trakt.tv

    auth
        {--f|force : Force run the flow, ignoring already existing credentials.}
    """

    def handle(self):
        from trakt_scrobbler import trakt_interface as ti
        from datetime import date

        if self.option("force"):
            self.line("Forcing trakt authentication")
            ti.TRAKT_TOKEN_PATH.unlink(missing_ok=True)
        if not ti.get_access_token():
            self.line("Failed to retrieve trakt token.", "error")
            return 1
        expiry = date.fromtimestamp(
            ti.token_data["created_at"] + ti.token_data["expires_in"]
        )
        self.line(f"Token valid until: {expiry}")
