import sys
from utils import config

APP_NAME = 'Trakt Scrobbler'

if config['general']['enable_notifs']:
    if sys.platform == 'win32':
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
    elif sys.platform == 'darwin':
        import subprocess as sp
    else:
        import notify2
        notify2.init(APP_NAME)


def notify(body, title=APP_NAME, timeout=5):
    if not config['general']['enable_notifs']:
        print(title, body)
        return
    if sys.platform == 'win32':
        toaster.show_toast(title, body, duration=timeout, threaded=True)
    elif sys.platform == 'darwin':
        osa_cmd = f'display notification "{body}" with title "{title}"'
        sp.run(["osascript", "-e", osa_cmd])
    else:
        notif = notify2.Notification(title, body)
        notif.timeout = timeout * 1000
        notif.show()
