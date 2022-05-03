import sys
import subprocess as sp
from copy import deepcopy

import confuse

from trakt_scrobbler import config, logger

APP_NAME = 'Trakt Scrobbler'


class NotifCategories(confuse.Template):
    """A template that returns the set of enabled categories"""
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

    def merge_categories(self, view, root: dict, user, default=True, parents=[]):
        """Merge data from user config with default categories"""
        if not isinstance(user, (dict, bool)):
            self.fail(f"Invalid value {user} for category {'.'.join(parents)}", view)
        if isinstance(user, dict):
            # check for extra keys not present in existing categories
            extra = set(user.keys()).difference(root)
            if extra:
                msg = f"Extra categor{'ies' if len(extra) > 1 else 'y'}"
                if parents:
                    msg += f" under {'.'.join(parents)}"
                msg += f": {', '.join(extra)}"
                self.fail(msg, view)

        for k, v in root.items():
            value = user if isinstance(user, bool) else user.get(k, default)
            if v:  # recurse for sub-categories
                parents.append(k)
                self.merge_categories(view, v, value, default)
                parents.pop()
            elif isinstance(value, bool):
                root[k] = value
            else:
                self.fail(
                    f"Expected bool(true/false) but found {value} for category " +
                    '.'.join(parents + [k]), view, True
                )

    def convert(self, value, view):
        # TODO: Parse this data to allow enabling only subcategories
        # Example: scrobble=False, scrobble.stop=True
        # currently, user would have to specify all subcategories of scrobble
        categories = deepcopy(self.CATEGORIES)
        self.merge_categories(view, categories, value)
        enabled_categories = set(flatten_categories(categories))
        logger.debug("Notifications enabled for categories: " +
                     ', '.join(sorted(enabled_categories)))
        if enabled_categories:
            import_deps()  # needed to handle case when cats are enabled later
        return enabled_categories


def flatten_categories(categories: dict, parents=[]):
    """Prepare the category data by flattening them into a string"""
    for k, v in categories.items():
        if isinstance(v, dict):
            parents.append(k)
            yield from flatten_categories(v, parents)
            parents.pop()
        elif v is True:
            yield '.'.join(parents + [k])


enabled_categories = config['general']['enable_notifs'].get_handle(NotifCategories())
imported, toaster, new_method_call, dbus_connection, notifier = [None] * 5


def import_deps():
    global imported, toaster, new_method_call, dbus_connection, notifier
    if imported:
        return
    imported = True
    if sys.platform == 'win32':
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
    elif sys.platform == 'darwin':
        pass
    else:
        try:
            from jeepney import DBusAddress, new_method_call as nmc
            from jeepney.io.blocking import open_dbus_connection
        except (ImportError, ModuleNotFoundError):
            # use notify-send via subprocess
            pass
        else:
            try:
                dbus_connection = open_dbus_connection(bus='SESSION')
            except Exception as e:
                logger.warning(f"Could not connect to DBUS: {e}")
                logger.warning("Disabling notifications")
                enabled_categories.clear()
            else:
                notifier = DBusAddress('/org/freedesktop/Notifications',
                                       bus_name='org.freedesktop.Notifications',
                                       interface='org.freedesktop.Notifications')
                new_method_call = nmc


def notify(body, title=APP_NAME, timeout=5, stdout=False, category="misc"):
    if stdout:
        print(body)
    if category not in enabled_categories.get():
        return
    if sys.platform == 'win32':
        toaster.show_toast(title, body, duration=timeout, threaded=True)
    elif sys.platform == 'darwin':
        osa_cmd = f'display notification "{body}" with title "{title}"'
        sp.run(["osascript", "-e", osa_cmd], check=False)
    elif notifier is not None and new_method_call is not None:
        msg = new_method_call(notifier, 'Notify', 'susssasa{sv}i',
                              (
                                  APP_NAME,
                                  0,  # do not replace notif
                                  'dialog-information',
                                  title,
                                  body,
                                  [], {},  # actions, hints
                                  timeout * 1000,
                              ))
        dbus_connection.send(msg)
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
