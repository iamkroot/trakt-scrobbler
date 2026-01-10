import typer

from . import CMD_NAME
from .config import app as config_app
from .trakt import app as trakt_app

app = typer.Typer(name=CMD_NAME, no_args_is_help=True)
app.add_typer(config_app)
app.add_typer(trakt_app)


if __name__ == "__main__":
    app()
