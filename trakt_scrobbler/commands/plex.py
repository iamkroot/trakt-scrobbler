from .command import Command
from trakt_scrobbler import logger
from trakt_scrobbler.utils import safe_request


class PlexAuthCommand(Command):
    """
    Runs the authentication flow for trakt.tv

    plex
        {--f|force : Force run the flow, ignoring already existing credentials}
        {--t|token=? : Enter plex token directly instead of password. Implies <c1>-f</>}
    """

    @staticmethod
    def plex_token_auth(login, password):
        auth_params = {
            "url": "https://plex.tv/users/sign_in.json",
            "data": {"user[login]": login, "user[password]": password},
            "headers": {
                "X-Plex-Client-Identifier": "com.iamkroot.trakt_scrobbler",
                "X-Plex-Product": "Trakt Scrobbler",
                "Accept": "application/json",
            },
        }
        return safe_request("post", auth_params)

    def get_token(self):
        logger.info("Retrieving plex token")
        login = self.ask("Plex login ID:")
        pwd = self.secret("Plex password:")
        resp = self.plex_token_auth(login, pwd)
        if resp:
            return resp.json()["user"]["authToken"]
        elif resp is not None:
            err_msg = resp.json().get("error", resp.text)
            self.line(err_msg, "error")
            logger.error(err_msg)
            return None
        else:
            logger.error("Unable to get access token")
            return None

    def handle(self):
        from trakt_scrobbler.player_monitors.plex import token

        if self.option("force"):
            del token.data
            self.line("Forcing plex authentication")

        token_data = self.option("token")
        if token_data is not None:
            if token_data == 'null':
                token_data = self.ask("Enter token:")
            # TODO: Verify that token is valid
            token.data = token_data
        elif not token:
            token_data = self.get_token()
            if token_data:
                token.data = token_data
                logger.info("Saved plex token")

        if token:
            self.line("Plex token is saved.")
        else:
            self.line("Failed to retrieve plex token.", "error")
            return 1
