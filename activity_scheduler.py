import asyncio
from collections.abc import Awaitable, Callable


Dispatcher = Callable[[dict, dict, list[dict]], Awaitable[bool]]
ActivityKey = tuple[int | None, str | None, str, str | None]


class ActivityDispatchCoordinator:
    def __init__(
        self,
        dispatcher: Dispatcher,
        delay_seconds: float = 8.0,
    ) -> None:
        self._dispatcher = dispatcher
        self._delay_seconds = delay_seconds
        self._lock = asyncio.Lock()
        self._current_key: ActivityKey | None = None
        self._pending_task: asyncio.Task | None = None

    async def reset(self) -> None:
        async with self._lock:
            self._cancel_pending()
            self._current_key = None

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
                print("[GO] SKIP | no active session", flush=True)
                return

            activity = dict(event)
            activity["durationSeconds"] = self._delay_seconds
            self._pending_task = asyncio.create_task(
                self._dispatch_after_delay(
                    key,
                    dict(session),
                    activity,
                    [dict(item) for item in recent_context],
                )
            )

    async def _dispatch_after_delay(
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

            await self._dispatcher(session, activity, recent_context)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            print(f"[GO] ERROR | dispatch scheduling failed: {error}", flush=True)

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
