import os
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, field_validator

from actor.notifications import send_nudge
from brain.evaluator import evaluate_activity
from evaluation_scheduler import ActivityEvaluationCoordinator


app = FastAPI(title="IntentGuard", version="0.1.0")

MAX_RECENT_EVENTS = 250
_state_lock = Lock()
_active_session: dict | None = None
_recent_events: deque[dict] = deque(maxlen=MAX_RECENT_EVENTS)
_evaluation_coordinator = ActivityEvaluationCoordinator(
    evaluator=evaluate_activity,
    notifier=send_nudge,
    delay_seconds=float(os.environ.get("INTENTGUARD_EVALUATION_DELAY_SECONDS", "8")),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionStart(BaseModel):
    goal: str = Field(min_length=1)

    @field_validator("goal")
    @classmethod
    def goal_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("goal must not be blank")
        return value


class ActivityEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    event_type: Literal["activity_start", "activity_end"]
    timestamp: str
    tabId: int | None = None
    windowId: int | None = None
    url: str | None = None
    domain: str | None = None
    title: str = ""
    reason: str | None = None
    startedAt: str | None = None
    endedAt: str | None = None
    durationSeconds: int | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/session/start")
async def start_session(request: SessionStart) -> dict:
    session = {
        "id": str(uuid4()),
        "goal": request.goal,
        "startedAt": utc_now_iso(),
    }

    with _state_lock:
        global _active_session
        _active_session = session
        _recent_events.clear()

    await _evaluation_coordinator.reset()

    print(f"[SESSION] {session['goal']}", flush=True)
    return {"session": session}


@app.get("/session")
def get_session() -> dict:
    with _state_lock:
        session = dict(_active_session) if _active_session else None
    return {"session": session}


@app.post("/activity")
async def record_activity(event: ActivityEvent) -> dict:
    stored_event = event.model_dump()

    with _state_lock:
        session_id = _active_session["id"] if _active_session else None
        stored_event["sessionId"] = session_id
        _recent_events.append(stored_event)
        session = dict(_active_session) if _active_session else None
        recent_context = list(_recent_events)[-5:]

    if event.event_type == "activity_start":
        print(f"[START] {event.domain or '-'} | {event.title}", flush=True)
    else:
        duration = event.durationSeconds if event.durationSeconds is not None else "?"
        print(f"[END]   {event.domain or '-'} | {duration}s | {event.title}", flush=True)

    try:
        await _evaluation_coordinator.handle_event(
            stored_event,
            session,
            recent_context,
        )
    except Exception as error:
        # Activity recording must remain available even if evaluation scheduling fails.
        print(f"[EVAL] ERROR | scheduler failed: {error}", flush=True)

    return {"accepted": True}


@app.get("/activity/recent")
def recent_activity() -> dict:
    with _state_lock:
        session = dict(_active_session) if _active_session else None
        events = list(_recent_events)

    return {
        "session": session,
        "events": events,
        "limit": MAX_RECENT_EVENTS,
    }
