import typer

from .console import console

app = typer.Typer(
    name="config", help="Edits the scrobbler config settings.", no_args_is_help=True
)


def _print_cfg(cfg: dict, prefix=""):
    for k, v in cfg.items():
        key = prefix + k
        if isinstance(v, dict):
            _print_cfg(v, key + ".")
        else:
            console.print(f"[info]{key}[/] = [comment]{v!r}[/]")


@app.command(
    name="list",
    help="Lists configuration settings. By default, only overridden values are shown.",
)
def list_(all: bool = typer.Option(False, help="Include default values too")):
    import confuse

    from trakt_scrobbler import config

    if all:
        _print_cfg(config.flatten())
    else:
        sources = [s for s in config.sources if not s.default]
        temp_root = confuse.RootView(sources)
        _print_cfg(temp_root.flatten())


def set_(all):
    pass
