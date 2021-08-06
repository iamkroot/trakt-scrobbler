import sys
from copy import deepcopy

from trakt_scrobbler import config, logger

APP_NAME = 'Trakt Scrobbler'
CATEGORIES = {
    "exception": {},
    "misc": {},
    "scrobble": {
        "start": {},
        "pause": {},
        "resume": {},
        "stop": {}
    },
    "trakt": {}
}


def merge_categories(root: dict, user, default=True, parents=[]):
    """Merge data from user config with default categories"""
    if not isinstance(user, (dict, bool)):
        logger.error(f"Invalid value {user} for category {'.'.join(parents)}")
        return
    if isinstance(user, dict):
        # check for extra keys not present in existing categories
        extra = set(user.keys()).difference(root)
        if extra:
            msg = f"Extra categor{'ies' if len(extra) > 1 else 'y'}"
            if parents:
                msg += f" under {'.'.join(parents)}"
            msg += f": {', '.join(extra)}"
            logger.warning(msg)

    for k, v in root.items():
        value = user if isinstance(user, bool) else user.get(k, default)
        if v:  # recurse for sub-categories
            parents.append(k)
            merge_categories(v, value, default)
            parents.pop()
        elif isinstance(value, bool):
            root[k] = value
        else:
            logger.error(
                f"Expected bool(true/false) but found {value} for category "
                f"{'.'.join(parents + [k])}"
            )


def flatten_categories(categories: dict, parents=[]):
    """Prepare the category data by flattening them into a string"""
    for k, v in categories.items():
        if isinstance(v, dict):
            parents.append(k)
            yield from flatten_categories(v, parents)
            parents.pop()
        elif v is True:
            yield '.'.join(parents + [k])


# TODO: Parse this data to allow enabling only subcategories
# Example: scrobble=False, scrobble.stop=True
# currently, user would have to specify all subcategories of scrobble
user_notif_categories = config['general']['enable_notifs'].get()
categories = deepcopy(CATEGORIES)
merge_categories(categories, user_notif_categories)
enabled_categories = set(flatten_categories(categories))

if enabled_categories:
    logger.debug("Notifications enabled for categories: "
                 f"{', '.join(sorted(enabled_categories))}")
    if sys.platform == 'win32':
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
    elif sys.platform == 'darwin':
        import subprocess as sp
    else:
        try:
            from jeepney import DBusAddress, new_method_call
            from jeepney.io.blocking import open_dbus_connection
        except (ImportError, ModuleNotFoundError):
            import subprocess as sp
            notifier = None
        else:
            try:
                dbus_connection = open_dbus_connection(bus='SESSION')
            except KeyError as e:
                logger.warning(f"Could not connect to DBUS: {e}")
                logger.warning("Disabling notifications")
                enabled_categories.clear()
                notifier = None
            else:
                notifier = DBusAddress('/org/freedesktop/Notifications',
                                       bus_name='org.freedesktop.Notifications',
                                       interface='org.freedesktop.Notifications')


def dbus_notify(title, body, timeout):
    msg = new_method_call(notifier, 'Notify', 'susssasa{sv}i',
                          (
                              APP_NAME,
                              0,  # do not replace notif
                              'dialog-information',
                              title,
                              body,
                              [], {},  # actions, hints
                              timeout,
                          ))
    dbus_connection.send(msg)


def notify(body, title=APP_NAME, timeout=5, stdout=False, category="misc"):
    if stdout:
        print(body)
    if category not in enabled_categories:
        return
    if sys.platform == 'win32':
        toaster.show_toast(title, body, duration=timeout, threaded=True)
    elif sys.platform == 'darwin':
        osa_cmd = f'display notification "{body}" with title "{title}"'
        sp.run(["osascript", "-e", osa_cmd], check=False)
    elif notifier is not None:
        dbus_notify(title, body, timeout * 1000)
    else:
        try:
            sp.run([
                "notify-send",
                "-a", title,
                "-i", 'dialog-information',
                "-t", str(timeout * 1000),
                title,
                body
            ], check=False)
        except FileNotFoundError:
            logger.exception("Unable to send notification")
            # disable all future notifications until app restart
            enabled_categories.clear()
