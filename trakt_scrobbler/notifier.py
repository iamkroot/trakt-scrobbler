import sys
import confuse
import subprocess as sp
from trakt_scrobbler import config, logger


class Singleton(type):
    def __init__(self, name, bases, mmbs):
        super().__init__(name, bases, mmbs)
        self._instance = super().__call__()

    def __call__(self):
        return self._instance


class Notifier(metaclass=Singleton):
    APP_NAME = 'Trakt Scrobbler'

    def __init__(self) -> None:
        self.enable_notifs = config['general']['enable_notifs'].get(
            confuse.Choice([True, False], default=True)
        )
        if self.enable_notifs:
            self.import_deps()

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

    def notify(self, body, title=APP_NAME, timeout=5, stdout=False):
        if stdout or not self.enable_notifs:
            print(body)
        if not self.enable_notifs:
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
                self.enable_notifs = False

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
