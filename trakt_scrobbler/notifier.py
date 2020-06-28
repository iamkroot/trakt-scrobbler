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
        import subprocess as sp
        try:
            import gi
            gi.require_version('Notify', '0.7')
            from gi.repository import Notify
            Notify.init(APP_NAME)
            notifier = Notify.Notification.new(APP_NAME)
        except (ImportError, ModuleNotFoundError):
            notifier = None


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
        sp.run(["osascript", "-e", osa_cmd])
    elif notifier is not None:
        notifier.set_timeout(timeout * 1000)
        notifier.update(title, body, 'dialog-information')
        notifier.show()
    else:
        try:
            sp.run(["notify-send", "-a", title, "-t", str(timeout * 1000), body])
        except FileNotFoundError:
            logger.exception("Unable to send notification")
            enable_notifs = False  # disable all future notifications until app restart
