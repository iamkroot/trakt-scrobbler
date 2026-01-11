import typer

from . import CMD_NAME
from .autostart import app as autostart_app
from .backlog import app as backlog_app
from .config import app as config_app
from .init import app as init_app
from .log import app as log_app
from .lookup import app as lookup_app
from .plex import app as plex_app
from .remap import app as remap_app
from .run import app as run_app
from .start import app as start_app
from .status import app as status_app
from .stop import app as stop_app
from .test import app as test_app
from .trakt import app as trakt_app
from .whitelist import app as whitelist_app

app = typer.Typer(name=CMD_NAME, no_args_is_help=True)
"""
For subcommands with single command (like `trakts status`, `trakts init`)
 1. We should _not_ specify a `name` field. That will end up with `trakts status status`.
      This happens because we use sub_app.command instead of sub_app.callback.
      Callback breaks arg parsing somehow.
 2. The above also means we need to provide help to the main command instead of the sub_app.
"""
app.add_typer(trakt_app)
app.add_typer(autostart_app, name="autostart")
app.add_typer(backlog_app, name="backlog")
app.add_typer(config_app, name="config")
app.add_typer(init_app)
app.add_typer(log_app, name="log")
app.add_typer(lookup_app)
app.add_typer(plex_app, name="plex")
app.add_typer(remap_app, name="remap")
app.add_typer(run_app)
app.add_typer(start_app)
app.add_typer(status_app)
app.add_typer(stop_app)
app.add_typer(test_app)
app.add_typer(whitelist_app, name="whitelist")


if __name__ == "__main__":
    app()
