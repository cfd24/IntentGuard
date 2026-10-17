import asyncio
from collections.abc import Awaitable, Callable

from brain.evaluator import Decision


Evaluator = Callable[[str, dict, list[dict]], Awaitable[Decision]]
Notifier = Callable[[str, Decision], Awaitable[None]]
ActivityKey = tuple[int | None, str | None, str, str | None]
MIN_NUDGE_CONFIDENCE = 0.85


class ActivityEvaluationCoordinator:
    def __init__(
        self,
        evaluator: Evaluator,
        notifier: Notifier,
        delay_seconds: float = 8.0,
    ) -> None:
        self._evaluator = evaluator
        self._notifier = notifier
        self._delay_seconds = delay_seconds
        self._lock = asyncio.Lock()
        self._current_key: ActivityKey | None = None
        self._pending_task: asyncio.Task | None = None
        self._notified_key: ActivityKey | None = None

    async def reset(self) -> None:
        async with self._lock:
            self._cancel_pending()
            self._current_key = None
            self._notified_key = None

    async def handle_event(
        self,
        event: dict,
        session: dict | None,
        recent_context: list[dict],
    ) -> None:
        key = self._activity_key(event)

        async with self._lock:
            if event["event_type"] == "activity_end":
                if key == self._current_key:
                    self._cancel_pending()
                    self._current_key = None
                return

            if key == self._current_key:
                return

            self._cancel_pending()
            self._current_key = key

            if session is None:
                return

            activity = dict(event)
            activity["durationSeconds"] = self._delay_seconds
            self._pending_task = asyncio.create_task(
                self._evaluate_after_delay(
                    key,
                    dict(session),
                    activity,
                    [dict(item) for item in recent_context],
                )
            )

    async def _evaluate_after_delay(
        self,
        key: ActivityKey,
        session: dict,
        activity: dict,
        recent_context: list[dict],
    ) -> None:
        try:
            await asyncio.sleep(self._delay_seconds)

            async with self._lock:
                if key != self._current_key:
                    return

            decision = await self._evaluator(
                session["goal"],
                activity,
                recent_context,
            )
            if (
                decision.decision == "NUDGE"
                and decision.confidence < MIN_NUDGE_CONFIDENCE
            ):
                decision = Decision(
                    decision="UNCERTAIN",
                    confidence=decision.confidence,
                    reason=decision.reason,
                )

            async with self._lock:
                if key != self._current_key:
                    return

                should_notify = (
                    decision.decision == "NUDGE" and key != self._notified_key
                )
                if should_notify:
                    self._notified_key = key

            print(
                f"[EVAL] {decision.decision} | confidence={decision.confidence:.2f} "
                f"| {decision.reason}",
                flush=True,
            )

            if should_notify:
                try:
                    await self._notifier(session["goal"], decision)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    print(f"[NOTIFY] ERROR | {error}", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"[EVAL] ERROR | {error}", flush=True)

    def _cancel_pending(self) -> None:
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
        self._pending_task = None

    @staticmethod
    def _activity_key(event: dict) -> ActivityKey:
        return (
            event.get("tabId"),
            event.get("url"),
            event.get("title", ""),
            event.get("startedAt"),
        )
