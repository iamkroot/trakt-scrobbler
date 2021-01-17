import sys
import confuse
from trakt_scrobbler import config, logger

APP_NAME = 'Trakt Scrobbler'
enable_notifs = config['general']['enable_notifs'].get(
    confuse.Choice([True, False], default=True)
)

if enable_notifs:
    if sys.platform == 'win32':
        from win10toast import ToastNotifier

        toaster = ToastNotifier()
    else:
        try:
            from jeepney import DBusAddress, new_method_call
            from jeepney.io.blocking import open_dbus_connection
        except (ImportError, ModuleNotFoundError):
            import subprocess as sp
            notifier, notif_id = None, None
        else:
            notifier = DBusAddress('/org/freedesktop/Notifications',
                                   bus_name='org.freedesktop.Notifications',
                                   interface='org.freedesktop.Notifications')
            notif_id = 0


def dbus_notify(title, body, timeout):
    global notif_id
    connection = open_dbus_connection(bus='SESSION')
    msg = new_method_call(notifier, 'Notify', 'susssasa{sv}i',
                          (
                              APP_NAME,
                              notif_id,
                              'dialog-information',
                              title,
                              body,
                              [], {},
                              timeout,
                          ))
    reply = connection.send_and_get_reply(msg)
    connection.close()
    notif_id = reply.body[0]


def notify(body, title=APP_NAME, timeout=5, stdout=False):
    global enable_notifs

    if stdout or not enable_notifs:
        print(body)
    if not enable_notifs:
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
            enable_notifs = False
