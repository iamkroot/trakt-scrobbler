from typing import Annotated

import typer

from . import CMD_NAME
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
            console.print(f"[info]{key}[/] = {v!r}")


@app.command(
    name="list",
    help="Lists configuration settings. By default, only overridden values are shown.",
)
def list_(
    all: Annotated[bool, typer.Option(help="Include default values too")] = False,
):
    import confuse

    from trakt_scrobbler import config

    if all:
        _print_cfg(config.flatten())
    else:
        sources = [s for s in config.sources if not s.default]
        temp_root = confuse.RootView(sources)
        _print_cfg(temp_root.flatten())


@app.command(
    name="set",
    short_help="Set the value for a config parameter.",
    help="""Set the value for a config parameter.

Separate multiple values with spaces.

Eg:

    [green]trakts config set players.monitored mpv vlc mpc-be[/]

For values containing space(s), surround them with double-quotes. Eg:

    [green]trakts config set fileinfo.whitelist D:\\Media\\Movies "C:\\Users\\My Name\\Shows"[/]

Use --add to avoid overwriting the previous list values (whitelist, monitored, etc.):

    [green]trakts config set players.monitored mpv vlc[/]
    [green]trakts config set --add players.monitored plex mpc-hc[/]

will have final value: [dim cyan]players.monitored[/] = [green]['mpv', 'vlc', 'plex', 'mpc-hc'][/]""",
)
def set_(
    key: str,
    values: list[str],
    add: Annotated[
        bool,
        typer.Option(
            help="In case of list values, add them to the end instead of overwriting"
        ),
    ] = False,
):
    # TODO: Add autocompletion for key
    TRUTHY_BOOL = ("true", "yes", "1")

    import confuse

    from trakt_scrobbler import config

    def handle_enable_notifs(config, view, key, values):
        if len(values) != 1:
            raise ValueError("Given parameter only accepts a single value")
        from trakt_scrobbler.notifier import CATEGORIES

        value = values[0].lower() in TRUTHY_BOOL

        view = view["general"]["enable_notifs"]
        user_cat = key.replace("general.enable_notifs", "").lstrip(".")
        if user_cat:
            heirarchy = user_cat.split(".")
            categories = CATEGORIES
            for sub_category in heirarchy:  # traverse down the heirarchy
                if sub_category not in categories:
                    raise KeyError(
                        f"[info]{sub_category}[/] is not a valid category name."
                    )
                categories = categories[sub_category]
                view = view[sub_category]
        view.set(value)

        save_config(config)
        console.print(
            f"User config updated with [info]{key}[/] = [comment]{value!r}[/]"
        )
        console.print(
            "Don't forget to restart the service for the changes to take effect."
        )

    view = config
    key = key.strip(".")

    # special case for notification categories
    if key.startswith("general.enable_notifs"):
        return handle_enable_notifs(config, view, key, values)

    # fix path escaping due to trailing backslash for windows
    values = [val[:-1] if val.endswith(r"\\") else val for val in values]

    for name in key.split("."):
        view = view[name]

    try:
        orig_val = view.get()
        if isinstance(orig_val, dict):
            raise confuse.ConfigTypeError
    except confuse.ConfigTypeError:
        console.print(f"Leaf key [info]{key}[/] not found in user config.", "error")
        console.print(
            f"Run [question]{CMD_NAME} config list --all[/] to see all "
            "possible keys and their current values."
        )
        return 1
    except confuse.NotFoundError:
        value = values[0] if len(values) == 1 else values
        view.add(value)
    else:
        if isinstance(orig_val, list):
            if add:
                value = list(set(orig_val).union(values))
            else:
                value = values
        elif len(values) == 1:
            if isinstance(orig_val, bool):
                value = values[0].lower() in TRUTHY_BOOL
            else:
                value = orig_val.__class__(values[0])
        else:
            console.print("Given parameter only accepts a single value", "error")
            return 1
        view.set(value)

    save_config(config)
    console.print(f"User config updated with [info]{key}[/] = {value!r}")
    console.print("Don't forget to restart the service for the changes to take effect.")


@app.command(help="Reset a config value to its default.")
def unset(key: str):
    import confuse

    from trakt_scrobbler import config

    *parts, name = key.split(".")
    sources = [s for s in config.sources if not s.default]
    temp_root = confuse.RootView(sources)
    view = temp_root
    for part in parts:
        view = view[part]
    view = view[name]
    try:
        view.get()
    except confuse.NotFoundError:
        console.print(f"[info]{key}[/] not found in user config.", "error")
        console.print(
            f"Run [question]{CMD_NAME} config list[/] to see all user-defined values."
        )
        return 1

    for src in temp_root.sources:
        for part in parts:
            src = src[part]
        if name in src:
            del src[name]

    save_config(config)

    console.print(f"Successfully unset [info]{key}[/]")


def save_config(config):
    with open(config.user_config_path(), "w") as f:
        f.write(config.dump(full=False))
