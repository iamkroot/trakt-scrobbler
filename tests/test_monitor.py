import unittest
from unittest.mock import MagicMock, patch
from trakt_scrobbler.player_monitors.monitor import Monitor, State


class TestStateChange(unittest.TestCase):
    def setUp(self):
        self.media_infos = {
            "show1": {
                "title": "Breaking Bad",
                "season": 5,
                "episode": 13
            },
            "show2": {
                "title": "Westworld",
                "season": 2,
                "episode": 4
            }
        }

        self.mocked_queue = MagicMock()
        with patch('trakt_scrobbler.player_monitors.monitor.Thread'):
            self.mon = Monitor(self.mocked_queue)

    def test_empty(self):
        self.assertRaises(StopIteration, next, self.mon.decide_action(None, None))

    def test_normal(self):
        state = {
            "progress": 30,
            "media_info": self.media_infos["show1"],
            "state": State.Playing,
            "updated_at": 1
        }
        actions = tuple(self.mon.decide_action(None, state))
        self.assertTupleEqual(('scrobble',), actions)

        new_state = {
            "progress": 50,
            "media_info": self.media_infos["show1"],
            "state": State.Paused,
            "updated_at": 5
        }

        actions = tuple(self.mon.decide_action(state, new_state))
        self.assertTupleEqual(('scrobble',), actions)

    def test_preview(self):
        state_1 = {
            "progress": 90,
            "media_info": self.media_infos["show1"],
            "state": State.Playing,
            "updated_at": 1
        }
        actions = tuple(self.mon.decide_action(None, state_1))
        self.assertTupleEqual(('enter_preview',), actions)

        self.mon.preview = True

        state_2 = {
            "progress": 91,
            "media_info": self.media_infos["show1"],
            "state": State.Paused,
            "updated_at": 4
        }
        actions = tuple(self.mon.decide_action(state_1, state_2))
        self.assertTupleEqual(('pause_preview',), actions)

        state_3 = {
            "progress": 91,
            "media_info": self.media_infos["show1"],
            "state": State.Playing,
            "updated_at": 100
        }
        actions = tuple(self.mon.decide_action(state_2, state_3))
        self.assertTupleEqual(('resume_preview',), actions)

        state_4 = {
            "progress": 94,
            "media_info": self.media_infos["show1"],
            "state": State.Stopped,
            "updated_at": 110
        }
        actions = tuple(self.mon.decide_action(state_3, state_4))
        self.assertTupleEqual(('exit_preview',), actions)

        self.mon.preview = False

        state_5 = {
            "progress": 10,
            "media_info": self.media_infos["show1"],
            "state": State.Stopped,
            "updated_at": 115
        }
        actions = tuple(self.mon.decide_action(state_4, state_5))
        self.assertTupleEqual(('scrobble',), actions)

        actions = tuple(self.mon.decide_action(None, state_2))
        self.assertTupleEqual(('enter_preview',), actions)
