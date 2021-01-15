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
            from pydbus import SessionBus
        except (ImportError, ModuleNotFoundError):
            import subprocess as sp
            notifier, notif_id = None, None
        else:
            notifier = SessionBus().get('.Notifications')
            notif_id = 0


def notify(body, title=APP_NAME, timeout=5, stdout=False):
    global enable_notifs
    global notif_id

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
        notif_id = notifier.Notify(
            APP_NAME,
            notif_id,
            'dialog-information',
            title,
            body,
            None,
            None,
            timeout * 1000
        )
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
