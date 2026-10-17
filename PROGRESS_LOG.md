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

### Semantic evaluation and intervention
* **Debounce architecture** — Each `activity_start` creates one cancellable evaluation task. It waits 8 seconds by default; an `activity_end`, replacement activity, or new session cancels the pending task. There is no continuous polling.
* **Decision boundary** — `brain/evaluator.py` sends only the active goal and browser text metadata to Gemini and returns `decision`, `confidence`, and `reason`. Valid decisions are `IGNORE`, `NUDGE`, and `UNCERTAIN`. Low-confidence NUDGE results are downgraded to UNCERTAIN.
* **Intervention boundary** — `actor/notifications.py` uses `osascript` for one concise macOS notification only after a clear NUDGE. IGNORE and UNCERTAIN never notify, and an unchanged activity cannot notify twice.
* **Failure behavior** — Provider and notification failures are logged without rejecting activity events or stopping the observer.

Required environment variable:
```bash
export GEMINI_API_KEY='your_api_key'
```

Optional configuration:
```bash
export INTENTGUARD_GEMINI_MODEL='gemini-2.5-flash'
export INTENTGUARD_GEMINI_TIMEOUT_SECONDS=20
export INTENTGUARD_EVALUATION_DELAY_SECONDS=8
```

Automated validation:
```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q main.py brain actor evaluation_scheduler.py tests
```

The automated suite mocks Gemini and macOS notifications. It verifies short-activity cancellation, replacement cancellation, stale in-flight result suppression, exactly-once evaluation, no-session behavior, all three decisions, low-confidence NUDGE safety, duplicate suppression, provider-failure isolation, session state, and the bounded activity timeline.

### Manual semantic test
1. Start the backend with `GEMINI_API_KEY` set, start a session with the Math 185 goal, and keep the backend terminal visible.
2. Open complex-logarithm material for more than 8 seconds. Expect `[EVAL] IGNORE` and no notification.
3. Open an unrelated page for only 2–5 seconds, then leave. Expect no `[EVAL]` line and no notification.
4. Open Dodgers/baseball highlights for more than 8 seconds. Expect a high-confidence `[EVAL] NUDGE` and one macOS notification. Remain on the unchanged page and confirm there is no second notification.
5. Open a page with an ambiguous title for more than 8 seconds. Expect `[EVAL] UNCERTAIN` or conservative IGNORE and no notification.
6. Stop the backend or temporarily remove the API key. Confirm browser activity continues to appear after recovery; model failures should log `[EVAL] ERROR` rather than break `/activity`.

### Known limitations and next step
* Sessions and events are in memory and reset whenever the backend restarts.
* Events generated while the backend is offline are not queued or replayed.
* Observation is limited to supported browser URLs; there is no desktop observer in this slice.
* Evaluation is text-only and depends on the quality of page titles and URLs.
* A navigation cancels stale results and notifications, but an already-started HTTP request may still finish in its worker thread.
* Evaluation decisions are logged but are not yet included in `/activity/recent` or persisted for review.
* **Next increment:** add evaluation decisions to the session timeline and a small feedback endpoint for marking helpful nudges and false positives before introducing personalization.
