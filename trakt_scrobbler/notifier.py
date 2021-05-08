import subprocess as sp
import sys
from copy import deepcopy

from trakt_scrobbler import config, logger


class Singleton(type):
    def __init__(self, name, bases, mmbs):
        super().__init__(name, bases, mmbs)
        self._instance = super().__call__()

    def __call__(self):
        return self._instance


class Notifier(metaclass=Singleton):
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

    def __init__(self) -> None:
        self.enabled_categories = set()
        self.read_categories()
        if self.enabled_categories:
            logger.debug("Notifications enabled for categories: "
                         f"{', '.join(self.enabled_categories)}")
            self.import_deps()

    def read_categories(self):
        # TODO: Parse this data to allow reverse enables
        # Example: scrobble=False, scrobble.stop=True
        # currently, user would have to specify all subcategories of scrobble
        data = config['general']['enable_notifs'].get()
        categories = deepcopy(self.CATEGORIES)
        self.merge_categories(categories, data)
        self.flatten_categories(categories)

    @classmethod
    def merge_categories(cls, root: dict, user, default=True, parents=[]):
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
                cls.merge_categories(v, value, default)
                parents.pop()
            elif isinstance(value, bool):
                root[k] = value
            else:
                logger.error(
                    f"Expected bool but found {value} for category "
                    f"{'.'.join(parents + [k])}"
                )

    def flatten_categories(self, categories: dict, parents=[]):
        """Prepare the category data by flattening them into a string"""
        for k, v in categories.items():
            if isinstance(v, dict):
                parents.append(k)
                self.flatten_categories(v, parents)
                parents.pop()
            elif v is True:
                self.enabled_categories.add('.'.join(parents + [k]))

    def import_deps(self):
        if sys.platform == 'win32':
            from win10toast import ToastNotifier
            self.toaster = ToastNotifier()
        elif sys.platform == 'linux':
            try:
                from jeepney import DBusAddress, new_method_call
                from jeepney.io.blocking import open_dbus_connection
            except (ImportError, ModuleNotFoundError):
                # will fall back to subprocess using notiy-send
                self.notifier = None
            else:
                self.new_method_call = new_method_call
                self.connection = open_dbus_connection(bus='SESSION')
                self.notifier = DBusAddress('/org/freedesktop/Notifications',
                                            bus_name='org.freedesktop.Notifications',
                                            interface='org.freedesktop.Notifications')
                self.notif_id = 0

    def notify(self, body, title=APP_NAME, timeout=5, stdout=False, category="misc"):
        if stdout:
            print(body)
        if category not in self.enabled_categories:
            return
        if sys.platform == 'win32':
            toaster.show_toast(title, body, duration=timeout, threaded=True)
        elif sys.platform == 'darwin':
            osa_cmd = f'display notification "{body}" with title "{title}"'
            sp.run(["osascript", "-e", osa_cmd], check=False)
        elif self.notifier is not None:
            self.dbus_notify(title, body, timeout * 1000)
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
                self.enabled_categories = set()

    def dbus_notify(self, title, body, timeout):
        msg = self.new_method_call(self.notifier, 'Notify', 'susssasa{sv}i',
                                   (
                                       self.APP_NAME,
                                       self.notif_id,  # replace notif
                                       'dialog-information',
                                       title,
                                       body,
                                       [], {},  # actions, hints
                                       timeout,
                                   ))
        reply = self.connection.send_and_get_reply(msg)
        self.notif_id = reply.body[0]
        if not isinstance(self.notif_id, int):
            self.notif_id = 0  # reset if some weird error occurred
