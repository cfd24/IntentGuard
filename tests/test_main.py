import unittest
from unittest.mock import patch

import main


class BackendStateTests(unittest.TestCase):
    def setUp(self):
        with main._state_lock:
            main._active_session = None
            main._recent_events.clear()

    @patch("builtins.print")
    def test_session_and_activity_timeline(self, _mock_print):
        session = main.start_session(main.SessionStart(goal="  Study logarithms  "))
        main.record_activity(
            main.ActivityEvent(
                event_type="activity_start",
                timestamp="2026-10-17T02:00:00Z",
                domain="example.com",
                title="Logarithms",
            )
        )

        recent = main.recent_activity()

        self.assertEqual(session["session"]["goal"], "Study logarithms")
        self.assertEqual(recent["session"], session["session"])
        self.assertEqual(len(recent["events"]), 1)
        self.assertEqual(recent["events"][0]["event_type"], "activity_start")
        self.assertEqual(recent["events"][0]["sessionId"], session["session"]["id"])

    @patch("builtins.print")
    def test_activity_timeline_is_bounded(self, _mock_print):
        for index in range(main.MAX_RECENT_EVENTS + 1):
            main.record_activity(
                main.ActivityEvent(
                    event_type="activity_start",
                    timestamp="2026-10-17T02:00:00Z",
                    title=str(index),
                )
            )

        events = main.recent_activity()["events"]

        self.assertEqual(len(events), main.MAX_RECENT_EVENTS)
        self.assertEqual(events[0]["title"], "1")


if __name__ == "__main__":
    unittest.main()
