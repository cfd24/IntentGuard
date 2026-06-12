# Project Roadmap - IntentGuard

## Project Overview
IntentGuard is a local macOS productivity agent. Unlike passive hosts-file blockers or simplistic web extensions, it uses multimodal AI to understand user context and behavior on a desktop level, dynamically intervening to enforce user-declared goals.

---

## What This Project Demonstrates to Recruiters
1. **Real-Time Agent Workflows**: Orchestrating asynchronous capture, evaluation, and system-level response loops in Python.
2. **Multimodal LLM Classification**: Practical utilization of Gemini/Anthropic APIs for real-time visual and semantic classification under latency constraints.
3. **Deep macOS System Integration**: Bridging high-level python scripts with macOS APIs (`pyobjc`, AppleScript, Accessibility APIs) for native control.
4. **Local-First Architecture**: Offline-ready SQLite database caching, local API server (FastAPI), and responsive UI (React/Vite).

---

## Feature Roadmap & Phases

### Phase 0: Setup & Core Brain (V0)
* [x] Spike screen capture and basic classification loop.
* [ ] Refactor spike into clean, tested `Brain` module with a unified `classify(screenshot, goal)` interface.
* [ ] Design database schemas for tracking sessions, logs, and user configs.

### Phase 1: Observer & System Integration (V1)
* [ ] Implement `Observer` module to collect active window titles and application names via `pyobjc`.
* [ ] Combine screenshot and window data to form richer LLM context inputs.
* [ ] Set up the local SQLite database to store user sessions and logs.

### Phase 2: Actor & Interventions (V2)
* [ ] Implement `Actor` intervention levels:
  * **Low**: Local system notifications (`pync`).
  * **Medium**: A full-screen blocking overlay with a text area requiring the user to re-verify/adjust their intent or ask for break time.
  * **High**: Active script intervention (focus lock).
* [ ] Build aggressiveness mapping (0-100% slider).

### Phase 3: Dashboard & Session Review (V3)
* [ ] Develop React-based menu-bar controls and dashboard.
* [ ] Log session summaries: duration, classification stats, and a list of drift events.
* [ ] "Review" flow: prompt the user at the end of a session to summarize what they accomplished.

### Phase 4: Personal Anchoring & Quotes (V4)
* [ ] Store and pull "past self" quotes written during sessions or reviews.
* [ ] Play back user's own quotes ("You promised yourself you'd finish the React layout before checking Twitter!") when drifting is detected.

---

## Notes for AI Coding Assistants
* Focus on keeping code modular and robust.
* Always write automated tests or validation scripts for the individual modules (Observer, Brain, Actor).
* Avoid building feature creep; execute Phase 0 and Phase 1 with stable foundations first.
