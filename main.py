from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, field_validator


app = FastAPI(title="IntentGuard", version="0.1.0")

MAX_RECENT_EVENTS = 250
_state_lock = Lock()
_active_session: dict | None = None
_recent_events: deque[dict] = deque(maxlen=MAX_RECENT_EVENTS)


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
def start_session(request: SessionStart) -> dict:
    session = {
        "id": str(uuid4()),
        "goal": request.goal,
        "startedAt": utc_now_iso(),
    }

    with _state_lock:
        global _active_session
        _active_session = session
        _recent_events.clear()

    print(f"[SESSION] {session['goal']}", flush=True)
    return {"session": session}


@app.get("/session")
def get_session() -> dict:
    with _state_lock:
        session = dict(_active_session) if _active_session else None
    return {"session": session}


@app.post("/activity")
def record_activity(event: ActivityEvent) -> dict:
    stored_event = event.model_dump()

    with _state_lock:
        session_id = _active_session["id"] if _active_session else None
        stored_event["sessionId"] = session_id
        _recent_events.append(stored_event)

    if event.event_type == "activity_start":
        print(f"[START] {event.domain or '-'} | {event.title}", flush=True)
    else:
        duration = event.durationSeconds if event.durationSeconds is not None else "?"
        print(f"[END]   {event.domain or '-'} | {duration}s | {event.title}", flush=True)

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
