# Progress Log - IntentGuard

## 2026-06-12
* **Project initialized.**
* **Spike prototype validated** — Created a single-file loop (`spike.py`) verifying that screen capture via `mss`/`Pillow` combined with Gemini Flash (`gemini-3.5-flash`) correctly classifies user focus state (`ON_TASK` vs `OFF_TASK`) in real time.
* **Documentation foundation set** — Added `AGENTS.md`, `aicontext.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `PROGRESS_LOG.md`, `SCRATCH.md`, and the task template.

## 2026-10-16
* **Local activity pipeline implemented** — Added a FastAPI backend with one active in-memory session, a bounded 250-event activity timeline, health/session/activity endpoints, and readable START/END terminal logs.
* **Chrome observer connected** — The existing Manifest V3 observer now POSTs activity start/end events to `http://127.0.0.1:8000/activity`. Current-activity persistence and existing console logs remain intact. Backend failures are warnings and do not stop observation.
* **Current architecture** — Chrome's event-driven tab/window observer sends activity events to the local FastAPI service, which associates them with the active session and exposes the recent timeline. The historical screenshot/LLM spike remains separate and unchanged.

### Run
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Start a session:
```bash
curl -X POST http://127.0.0.1:8000/session/start \
  -H 'Content-Type: application/json' \
  -d '{"goal":"Finish Math 185 homework on complex logarithms"}'
```

Inspect the service and timeline:
```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/session
curl http://127.0.0.1:8000/activity/recent
```

### Test
```bash
.venv/bin/python -m unittest discover -s tests
node --check chrome-extension/service_worker.js
python3 -m json.tool chrome-extension/manifest.json >/dev/null
```

In `chrome://extensions`, reload IntentGuard Observer once after this extension update so Chrome grants the new localhost host permission. With the backend running and a session active, switch among tabs and confirm START/END logs appear in both the extension service-worker console and backend terminal. Stop the backend, switch tabs, and confirm observation continues with a backend-unavailable warning. Restart the backend and switch tabs again; delivery resumes without another extension reload.

### Superhuman Go dispatch path
* **Architecture decision** — Superhuman Go is now the live semantic reasoning agent. Slack is a temporary event bridge used only to wake Go through its Slack Message Received trigger.
* **Persistence coordinator** — Each `activity_start` creates one cancellable task. It waits 8 seconds by default; an `activity_end`, replacement activity, or new session cancels the task. One unchanged activity can dispatch only once, with no continuous polling.
* **Stable identity and context** — Every activity start receives a UUID event ID. The Slack payload includes that ID, the session ID and goal, current URL/domain/title/duration, and at most three recent completed activities.
* **Default live behavior** — Persisted activity calls `go_dispatcher.dispatch_activity_to_go`. It does not invoke Gemini and does not send a local notification.
* **Fallback code retained** — `brain/evaluator.py`, `evaluation_scheduler.py`, and `actor/notifications.py` remain tested fallback/development code but are not imported by the live backend path.
* **Failure behavior** — Missing Slack configuration and Slack API failures log safe `[GO] ERROR` messages without rejecting activity events. Tokens and authorization headers are never logged.

Required live configuration:
```bash
export SLACK_USER_TOKEN='your_user_oauth_token'
export SLACK_CHANNEL_ID='your_channel_id'
```

`GEMINI_API_KEY` is not required for the live Go dispatch path. The existing Gemini variables in `.env.example` apply only to the inactive fallback evaluator.

Optional persistence configuration:
```bash
export INTENTGUARD_EVALUATION_DELAY_SECONDS=8
```

Automated validation:
```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q main.py activity_scheduler.py go_dispatcher.py brain actor evaluation_scheduler.py tests
node --check chrome-extension/service_worker.js
python3 -m json.tool chrome-extension/manifest.json >/dev/null
```

The suite mocks Slack, Gemini, and notification side effects. It verifies short/replaced activity cancellation, exactly-once dispatch, no-session behavior, safe configuration/API failures, token redaction, payload contents, UUID propagation, no Gemini call in the live dispatch path, the retained fallback evaluator, session state, and the bounded timeline.

### Manual Go dispatch test
1. Export `SLACK_USER_TOKEN` and `SLACK_CHANNEL_ID`, then start the backend and keep its terminal visible.
2. Start a session with the goal “Finish Math 185 homework on complex logarithms.”
3. Open a relevant page for less than 8 seconds and leave. Expect no Slack message and no Go wake-up.
4. Open Dodgers/baseball highlights and remain for more than 8 seconds. Expect one `[GO] DISPATCH` log, one automatic `INTENTGUARD_EVENT` in Slack, and a new Go run that reasons about the event.
5. Do not type anything manually in Slack. A Gemini API key is not needed.

### Known limitations and next step
* Sessions and events are in memory and reset whenever the backend restarts.
* Events generated while the backend is offline are not queued or replayed.
* Observation is limited to supported browser URLs; there is no desktop observer in this slice.
* Slack is a temporary wake bridge, and failed dispatches are not retried or queued.
* Go currently reasons about the event but cannot return a decision or action to IntentGuard automatically.
* An activity change cancels a pending dispatch, but a Slack HTTP request that has already started cannot be recalled.
* **Next architectural question:** define the clean Go → IntentGuard return/action path while preserving event IDs for correlation.
