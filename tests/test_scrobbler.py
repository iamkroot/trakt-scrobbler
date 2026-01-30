import unittest
from unittest.mock import MagicMock, patch

from trakt_scrobbler.scrobbler import Scrobbler


class TestScrobbler(unittest.TestCase):
    def test_skip_low_progress_pause(self):
        mocked_queue = MagicMock()
        mocked_backlog = MagicMock()
        scrobbler = Scrobbler(mocked_queue, mocked_backlog)
        data = {
            "progress": 0.5,
            "media_info": {"type": "episode", "title": "Test Show"},
        }

        with patch("trakt_scrobbler.trakt_interface.scrobble") as mocked_scrobble:
            scrobbler.scrobble("pause", data)

        mocked_scrobble.assert_not_called()
        self.assertEqual(("pause", data), scrobbler.prev_scrobble)


if __name__ == "__main__":
    unittest.main()
