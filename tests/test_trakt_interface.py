import unittest
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from trakt_scrobbler.trakt_interface import get_ids, prepare_history_data, prepare_scrobble_data, scrobble


class TestTraktInterfaceIds(unittest.TestCase):
    def test_get_ids_uses_guid_ids_for_movie(self):
        media_info = {
            "type": "movie",
            "title": "Example Movie",
            "ids": {"imdb": "tt1234567", "tmdb": 12345},
        }
        self.assertEqual(media_info["ids"], get_ids(media_info))

    def test_prepare_scrobble_data_episode_uses_ids(self):
        media_info = {
            "type": "episode",
            "title": "Example Show",
            "season": 1,
            "episode": 2,
            "show_ids": {"tvdb": 111},
            "episode_ids": {"tvdb": 222},
        }
        payload = prepare_scrobble_data(media_info)
        self.assertEqual({"tvdb": 111}, payload["show"]["ids"])
        self.assertEqual({"tvdb": 222}, payload["episode"]["ids"])
        self.assertNotIn("season", payload["episode"])
        self.assertNotIn("number", payload["episode"])

    def test_prepare_history_data_episode_uses_ids(self):
        media_info = {
            "type": "episode",
            "title": "Example Show",
            "season": 3,
            "episode": 4,
            "show_ids": {"tvdb": 333},
            "episode_ids": {"tvdb": 444},
        }
        payload = prepare_history_data("2026-01-30T00:00:00Z", media_info)
        show_payload = payload["shows"][0]
        episode_payload = show_payload["seasons"][0]["episodes"][0]
        self.assertEqual({"tvdb": 333}, show_payload["ids"])
        self.assertEqual({"tvdb": 444}, episode_payload["ids"])
        self.assertNotIn("number", episode_payload)

    def test_scrobble_retries_with_episode_ids_only(self):
        media_info = {
            "type": "episode",
            "title": "Hell's Paradise",
            "season": 2,
            "episode": 1,
            "show_ids": {"imdb": "tt13911284", "tmdb": 117465, "tvdb": 402474},
            "episode_ids": {"imdb": "tt35090625", "tmdb": 6862898, "tvdb": 10987440},
        }
        first_resp = MagicMock(status_code=HTTPStatus.NOT_FOUND)
        second_resp = MagicMock(status_code=HTTPStatus.OK)
        second_resp.json.return_value = {"ok": True}

        with patch('trakt_scrobbler.trakt_interface.safe_request') as mocked_request:
            mocked_request.side_effect = [first_resp, second_resp]
            result = scrobble('start', media_info, 0.0)

        self.assertEqual({"ok": True}, result)
        self.assertEqual(2, mocked_request.call_count)
        first_payload = mocked_request.call_args_list[0].args[1]["json"]
        second_payload = mocked_request.call_args_list[1].args[1]["json"]
        self.assertNotIn("show", first_payload)
        self.assertEqual(media_info["episode_ids"], first_payload["episode"]["ids"])
        self.assertIn("show", second_payload)
        self.assertIn("season", second_payload["episode"])
        self.assertIn("number", second_payload["episode"])


if __name__ == "__main__":
    unittest.main()
