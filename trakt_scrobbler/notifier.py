import sys
from utils import config

APP_NAME = 'Trakt Scrobbler'

if sys.platform != 'win32':
    import notify2
    notify2.init(APP_NAME)
else:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()


def notify(body, title=APP_NAME, timeout=5):
    if not config['general']['enable_notifs']:
        print(title, body)
        return
    if sys.platform != 'win32':
        notif = notify2.Notification(title, body)
        notif.timeout = timeout * 1000
        notif.show()
    else:
        toaster.show_toast(title, body, duration=timeout, threaded=True)
