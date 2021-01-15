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
        else:
            NOTIFIER = SessionBus().get('.Notifications')
            NOTIF_ID = 0


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
    elif 'SessionBus' in globals() and 'NOTIFIER' in globals():
        global NOTIFIER
        global NOTIF_ID
        NOTIF_ID = NOTIFIER.Notify(
            APP_NAME,
            NOTIF_ID,
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
            enable_notifs = False  # disable all future notifications until app restart
