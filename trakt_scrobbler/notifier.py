import asyncio
import threading
from copy import deepcopy
from typing import Sequence

import confuse
import sys

from desktop_notifier.main import Button

from trakt_scrobbler import config, logger, notifier, APP_NAME
CATEGORIES = {
    "exception": {},
    "misc": {},
    "scrobble": {"start": {}, "pause": {}, "resume": {}, "stop": {}},
    "trakt": {},
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
    logger.debug(
        "Notifications enabled for categories: "
        f"{', '.join(sorted(enabled_categories))}"
    )


notif_loop = asyncio.new_event_loop()

def notify_loop():
    logger.info("Starting notif loop")
    asyncio.set_event_loop(notif_loop)
    notif_loop.run_forever()
    logger.info("Ending notif loop")

notif_thread = threading.Thread(target=notify_loop, name="notify_loop", daemon=True)
notif_thread.start()

notif_action_categories = config['general']['notif_actions']['enabled'].get()
categories = deepcopy(CATEGORIES)
merge_categories(categories, notif_action_categories)
enabled_notif_action_categories = set(flatten_categories(categories))

notif_action_interface = config['general']['notif_actions']['primary_interface'].get(
    confuse.Choice(['button', 'click'], default='button')
)
logger.debug(
    "Notif actions enabled for categories: "
    f"{', '.join(sorted(enabled_notif_action_categories))}"
)


def notify(
    body,
    title=APP_NAME,
    timeout=5,
    stdout=False,
    category="misc",
    actions: Sequence[Button] = (),
):
    if stdout:
        print(body)
    if category not in enabled_categories:
        return
    if actions and category in enabled_notif_action_categories:
        if notif_action_interface == 'click':
            primary_action, *actions = actions
            on_clicked = primary_action.on_pressed
        else:
            on_clicked = None
    else:
        on_clicked = None
        actions = ()
    notif_task = notifier.send(
        title, body, icon="", on_clicked=on_clicked, buttons=actions
    )
    fut = asyncio.run_coroutine_threadsafe(notif_task, notif_loop)
    try:
        # wait for the notification to be _sent_
        # this timeout is _not_ the same as the duration for which notif is shown
        fut.result(timeout=1.0)
    except TimeoutError:
        logger.warning("Timed out trying to send notification")
    except asyncio.CancelledError:
        logger.warning("Notification future cancelled")
    except Exception as e:
        logger.error(f"Error when sending notification {e}")
