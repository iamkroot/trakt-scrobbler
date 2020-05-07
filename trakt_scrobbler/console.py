from trakt_scrobbler import __version__
from cleo import Application

from trakt_scrobbler.commands.command import CMD_NAME
from trakt_scrobbler.commands.autostart import AutostartCommand
from trakt_scrobbler.commands.backlog import BacklogCommand
from trakt_scrobbler.commands.config import ConfigCommand
from trakt_scrobbler.commands.init import InitCommand
from trakt_scrobbler.commands.log import LogCommand
from trakt_scrobbler.commands.plex import PlexAuthCommand
from trakt_scrobbler.commands.run import RunCommand
from trakt_scrobbler.commands.start import StartCommand
from trakt_scrobbler.commands.status import StatusCommand
from trakt_scrobbler.commands.stop import StopCommand
from trakt_scrobbler.commands.trakt import TraktAuthCommand
from trakt_scrobbler.commands.whitelist import WhitelistCommand


def main():
    application = Application(CMD_NAME, __version__)
    application.add(AutostartCommand())
    application.add(BacklogCommand())
    application.add(ConfigCommand())
    application.add(InitCommand())
    application.add(LogCommand())
    application.add(PlexAuthCommand())
    application.add(RunCommand())
    application.add(StartCommand())
    application.add(StatusCommand())
    application.add(StopCommand())
    application.add(TraktAuthCommand())
    application.add(WhitelistCommand())
    application.run()


if __name__ == '__main__':
    main()
