import inspect
from pathlib import Path
from importlib import import_module
from .monitor import Monitor


def collect_monitors():
    """Collect the monitors from 'player_monitors' package."""
    modules = Path(__file__).parent.glob("*.py")
    monitors = set()

    for module_path in modules:
        if module_path.stem == "__init__":
            continue  # exclude this file

        monitor_module = import_module(__name__ + "." + module_path.stem)
        # get the required Monitor subclasses
        for _, mon in inspect.getmembers(monitor_module, inspect.isclass):
            if issubclass(mon, Monitor) and not getattr(mon, "exclude_import", False):
                monitors.add(mon)
    return monitors
