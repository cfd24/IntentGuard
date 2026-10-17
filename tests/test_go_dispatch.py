import asyncio
import json
import os
import unittest
from io import BytesIO
from unittest.mock import AsyncMock, patch

from activity_scheduler import ActivityDispatchCoordinator
from go_dispatcher import (
    SlackDispatchError,
    _post_slack_message,
    build_intentguard_event,
    dispatch_activity_to_go,
)


SESSION = {
    "id": "session-1",
    "goal": "Finish Math 185 homework on complex logarithms",
}


def activity(number: int, event_type: str = "activity_start") -> dict:
    return {
        "event_type": event_type,
        "eventId": f"event-{number}",
        "tabId": number,
        "url": f"https://example.com/{number}",
        "domain": "example.com",
        "title": f"Activity {number}",
        "startedAt": f"2026-10-17T03:00:0{number}Z",
    }


class ActivityDispatchCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.coordinators = []

    async def asyncTearDown(self):
        for coordinator in self.coordinators:
            await coordinator.reset()
        await asyncio.sleep(0)

    def make_coordinator(self, dispatcher):
        coordinator = ActivityDispatchCoordinator(
            dispatcher=dispatcher,
            delay_seconds=0.01,
        )
        self.coordinators.append(coordinator)
        return coordinator

    async def wait_for_dispatch(self):
        await asyncio.sleep(0.03)

    async def test_short_activity_does_not_dispatch(self):
        dispatcher = AsyncMock()
        coordinator = self.make_coordinator(dispatcher)
        started = activity(1)

        await coordinator.handle_event(started, SESSION, [])
        await coordinator.handle_event(
            {**started, "event_type": "activity_end"},
            SESSION,
            [],
        )
        await self.wait_for_dispatch()

        dispatcher.assert_not_awaited()

    async def test_replaced_activity_does_not_dispatch_stale_event(self):
        dispatcher = AsyncMock(return_value=True)
        coordinator = self.make_coordinator(dispatcher)

        await coordinator.handle_event(activity(1), SESSION, [])
        await coordinator.handle_event(activity(2), SESSION, [])
        await self.wait_for_dispatch()

        dispatcher.assert_awaited_once()
        self.assertEqual(dispatcher.await_args.args[1]["eventId"], "event-2")

    async def test_persistent_activity_dispatches_exactly_once(self):
        dispatcher = AsyncMock(return_value=True)
        coordinator = self.make_coordinator(dispatcher)
        started = activity(1)

        await coordinator.handle_event(started, SESSION, [])
        await self.wait_for_dispatch()
        await coordinator.handle_event(started, SESSION, [])
        await self.wait_for_dispatch()

        dispatcher.assert_awaited_once()

    @patch("builtins.print")
    async def test_no_session_does_not_dispatch(self, _mock_print):
        dispatcher = AsyncMock()
        coordinator = self.make_coordinator(dispatcher)

        await coordinator.handle_event(activity(1), None, [])
        await self.wait_for_dispatch()

        dispatcher.assert_not_awaited()


class SlackDispatcherTests(unittest.IsolatedAsyncioTestCase):
    @patch("go_dispatcher.urlopen")
    def test_slack_http_request_uses_json_and_bearer_auth(self, open_url):
        open_url.return_value = BytesIO(b'{"ok": true}')

        _post_slack_message("test-token", "channel-1", "test message")

        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, "https://slack.com/api/chat.postMessage")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(
            json.loads(request.data),
            {"channel": "channel-1", "text": "test message"},
        )

    @patch("go_dispatcher.urlopen")
    def test_slack_error_response_raises_safe_error(self, open_url):
        open_url.return_value = BytesIO(b'{"ok": false, "error": "invalid_auth"}')

        with self.assertRaisesRegex(SlackDispatchError, "invalid_auth"):
            _post_slack_message("test-token", "channel-1", "test message")

    @patch.dict(os.environ, {}, clear=True)
    @patch("go_dispatcher._post_slack_message")
    @patch("builtins.print")
    async def test_missing_configuration_fails_safely(
        self,
        _mock_print,
        post_message,
    ):
        dispatched = await dispatch_activity_to_go(SESSION, activity(1), [])

        self.assertFalse(dispatched)
        post_message.assert_not_called()

    @patch.dict(
        os.environ,
        {"SLACK_USER_TOKEN": "test-token", "SLACK_CHANNEL_ID": "channel-1"},
        clear=True,
    )
    @patch("go_dispatcher._post_slack_message")
    @patch("builtins.print")
    async def test_slack_api_error_fails_safely(self, _mock_print, post_message):
        post_message.side_effect = SlackDispatchError("Slack API error: invalid_auth")

        dispatched = await dispatch_activity_to_go(SESSION, activity(1), [])

        self.assertFalse(dispatched)

    @patch.dict(
        os.environ,
        {"SLACK_USER_TOKEN": "sensitive-test-value", "SLACK_CHANNEL_ID": "channel-1"},
        clear=True,
    )
    @patch("go_dispatcher._post_slack_message")
    @patch("builtins.print")
    async def test_failure_log_redacts_token(self, mock_print, post_message):
        post_message.side_effect = RuntimeError(
            "unexpected sensitive-test-value failure"
        )

        dispatched = await dispatch_activity_to_go(SESSION, activity(1), [])

        self.assertFalse(dispatched)
        logged_text = " ".join(str(call) for call in mock_print.call_args_list)
        self.assertNotIn("sensitive-test-value", logged_text)
        self.assertIn("[redacted]", logged_text)

    def test_payload_contains_required_context(self):
        recent_context = [
            {
                "event_type": "activity_end",
                "domain": "google.com",
                "title": "complex logarithms",
                "durationSeconds": 18,
            }
        ]
        current = {
            **activity(1),
            "domain": "youtube.com",
            "title": "Dodgers vs Brewers NLCS Highlights",
            "url": "https://youtube.com/watch?v=example",
            "durationSeconds": 8,
        }

        payload = build_intentguard_event(SESSION, current, recent_context)

        self.assertIn("INTENTGUARD_EVENT", payload)
        self.assertIn("Event ID: event-1", payload)
        self.assertIn("Session ID: session-1", payload)
        self.assertIn(SESSION["goal"], payload)
        self.assertIn("Domain: youtube.com", payload)
        self.assertIn("Dodgers vs Brewers NLCS Highlights", payload)
        self.assertIn("https://youtube.com/watch?v=example", payload)
        self.assertIn("Duration: 8 seconds", payload)
        self.assertIn("google.com | complex logarithms | 18s", payload)

    @patch.dict(
        os.environ,
        {"SLACK_USER_TOKEN": "test-token", "SLACK_CHANNEL_ID": "channel-1"},
        clear=True,
    )
    @patch("go_dispatcher._post_slack_message")
    @patch("builtins.print")
    async def test_success_posts_once_without_gemini(
        self,
        _mock_print,
        post_message,
    ):
        with patch("brain.evaluator.evaluate_activity", new_callable=AsyncMock) as gemini:
            dispatched = await dispatch_activity_to_go(SESSION, activity(1), [])

        self.assertTrue(dispatched)
        post_message.assert_called_once()
        gemini.assert_not_awaited()
