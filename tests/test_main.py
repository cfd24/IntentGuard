import unittest
from unittest.mock import AsyncMock, patch

import main


class BackendStateTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with main._state_lock:
            main._active_session = None
            main._recent_events.clear()

    @patch.object(main, "_evaluation_coordinator", new_callable=AsyncMock)
    @patch("builtins.print")
    async def test_session_and_activity_timeline(self, _mock_print, coordinator):
        session = await main.start_session(
            main.SessionStart(goal="  Study logarithms  ")
        )
        await main.record_activity(
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
        coordinator.handle_event.assert_awaited_once()

    @patch.object(main, "_evaluation_coordinator", new_callable=AsyncMock)
    @patch("builtins.print")
    async def test_activity_timeline_is_bounded(self, _mock_print, _coordinator):
        for index in range(main.MAX_RECENT_EVENTS + 1):
            await main.record_activity(
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
