import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from brain.evaluator import Decision
from evaluation_scheduler import ActivityEvaluationCoordinator


SESSION = {"id": "session-1", "goal": "Finish Math 185 homework"}


def activity(number: int, event_type: str = "activity_start") -> dict:
    return {
        "event_type": event_type,
        "tabId": number,
        "url": f"https://example.com/{number}",
        "domain": "example.com",
        "title": f"Activity {number}",
        "startedAt": f"2026-10-17T02:00:0{number}Z",
    }


class EvaluationCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.coordinators = []

    async def asyncTearDown(self):
        for coordinator in self.coordinators:
            await coordinator.reset()
        await asyncio.sleep(0)

    def make_coordinator(self, evaluator, notifier):
        coordinator = ActivityEvaluationCoordinator(
            evaluator=evaluator,
            notifier=notifier,
            delay_seconds=0.01,
        )
        self.coordinators.append(coordinator)
        return coordinator

    async def wait_for_evaluation(self):
        await asyncio.sleep(0.03)

    async def test_short_activity_does_not_call_evaluator(self):
        evaluator = AsyncMock()
        coordinator = self.make_coordinator(evaluator, AsyncMock())
        started = activity(1)

        await coordinator.handle_event(started, SESSION, [])
        await coordinator.handle_event(
            {**started, "event_type": "activity_end"},
            SESSION,
            [],
        )
        await self.wait_for_evaluation()

        evaluator.assert_not_awaited()

    async def test_replaced_activity_does_not_evaluate_old_activity(self):
        evaluator = AsyncMock(
            return_value=Decision(
                decision="IGNORE",
                confidence=0.9,
                reason="Relevant activity",
            )
        )
        coordinator = self.make_coordinator(evaluator, AsyncMock())

        await coordinator.handle_event(activity(1), SESSION, [])
        await coordinator.handle_event(activity(2), SESSION, [])
        await self.wait_for_evaluation()

        evaluator.assert_awaited_once()
        self.assertEqual(evaluator.await_args.args[1]["title"], "Activity 2")

    async def test_replacement_during_evaluation_cannot_notify(self):
        evaluation_started = asyncio.Event()
        release_evaluation = asyncio.Event()

        async def delayed_nudge(_goal, _activity, _context):
            evaluation_started.set()
            await release_evaluation.wait()
            return Decision(
                decision="NUDGE",
                confidence=0.97,
                reason="Old activity was unrelated",
            )

        notifier = AsyncMock()
        coordinator = self.make_coordinator(delayed_nudge, notifier)

        await coordinator.handle_event(activity(1), SESSION, [])
        await evaluation_started.wait()
        await coordinator.handle_event(activity(2), None, [])
        release_evaluation.set()
        await asyncio.sleep(0)

        notifier.assert_not_awaited()

    async def test_persistent_activity_is_evaluated_exactly_once(self):
        evaluator = AsyncMock(
            return_value=Decision(
                decision="IGNORE",
                confidence=0.9,
                reason="Relevant activity",
            )
        )
        coordinator = self.make_coordinator(evaluator, AsyncMock())
        started = activity(1)

        await coordinator.handle_event(started, SESSION, [])
        await self.wait_for_evaluation()
        await coordinator.handle_event(started, SESSION, [])
        await self.wait_for_evaluation()

        evaluator.assert_awaited_once()

    async def test_no_session_skips_evaluation(self):
        evaluator = AsyncMock()
        coordinator = self.make_coordinator(evaluator, AsyncMock())

        await coordinator.handle_event(activity(1), None, [])
        await self.wait_for_evaluation()

        evaluator.assert_not_awaited()

    async def test_ignore_does_not_notify(self):
        notifier = await self.run_decision("IGNORE")
        notifier.assert_not_awaited()

    async def test_uncertain_does_not_notify(self):
        notifier = await self.run_decision("UNCERTAIN")
        notifier.assert_not_awaited()

    async def test_low_confidence_nudge_is_treated_as_uncertain(self):
        evaluator = AsyncMock(
            return_value=Decision(
                decision="NUDGE",
                confidence=0.6,
                reason="Possible conflict",
            )
        )
        notifier = AsyncMock()
        coordinator = self.make_coordinator(evaluator, notifier)

        await coordinator.handle_event(activity(1), SESSION, [])
        await self.wait_for_evaluation()

        notifier.assert_not_awaited()

    async def test_nudge_notifies(self):
        notifier = await self.run_decision("NUDGE")
        notifier.assert_awaited_once()

    async def test_duplicate_unchanged_nudge_does_not_notify_twice(self):
        decision = Decision(
            decision="NUDGE",
            confidence=0.97,
            reason="Clearly unrelated",
        )
        evaluator = AsyncMock(return_value=decision)
        notifier = AsyncMock()
        coordinator = self.make_coordinator(evaluator, notifier)
        started = activity(1)

        await coordinator.handle_event(started, SESSION, [])
        await self.wait_for_evaluation()
        await coordinator.handle_event(started, SESSION, [])
        await self.wait_for_evaluation()

        evaluator.assert_awaited_once()
        notifier.assert_awaited_once()

    @patch("builtins.print")
    async def test_provider_failure_does_not_break_future_events(self, _mock_print):
        evaluator = AsyncMock(
            side_effect=[
                RuntimeError("provider unavailable"),
                Decision(
                    decision="IGNORE",
                    confidence=0.9,
                    reason="Relevant activity",
                ),
            ]
        )
        notifier = AsyncMock()
        coordinator = self.make_coordinator(evaluator, notifier)

        await coordinator.handle_event(activity(1), SESSION, [])
        await self.wait_for_evaluation()
        await coordinator.handle_event(activity(2), SESSION, [])
        await self.wait_for_evaluation()

        self.assertEqual(evaluator.await_count, 2)
        notifier.assert_not_awaited()

    async def run_decision(self, decision_name: str):
        decision = Decision(
            decision=decision_name,
            confidence=0.97,
            reason="Test decision",
        )
        notifier = AsyncMock()
        coordinator = self.make_coordinator(
            AsyncMock(return_value=decision),
            notifier,
        )

        await coordinator.handle_event(activity(1), SESSION, [])
        await self.wait_for_evaluation()
        return notifier
