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

### Known limitations and next step
* Sessions and events are in memory and reset whenever the backend restarts.
* Events generated while the backend is offline are not queued or replayed.
* Observation is limited to supported browser URLs; there is no desktop observer in this slice.
* No semantic classification or intervention is implemented yet.
* **Next increment:** add a short activity-change debounce/persistence threshold, then evaluate stable activity against the active goal and trigger a local notification.
