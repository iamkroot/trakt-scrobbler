import inspect
from pkgutil import iter_modules
from importlib import import_module
from .monitor import Monitor, WebInterfaceMon
import os


pkgname = __package__
pkgpath = os.path.dirname(__file__)


def collect_monitors():
    """Collect the monitors from 'player_monitors' package."""
    monitors = set()
    for mod in iter_modules([pkgpath], prefix=f"{pkgname}."):
        if mod.name.endswith(".monitor"):
            # exclude the base package
            continue
        monitor_module = import_module(mod.name)
        # get the required Monitor subclasses
        for _, Mon in inspect.getmembers(monitor_module, inspect.isclass):
            if (
                issubclass(Mon, Monitor)
                and Mon != Monitor
                and Mon != WebInterfaceMon
                and not getattr(Mon, "exclude_import", False)
            ):
                monitors.add(Mon)
    return monitors
