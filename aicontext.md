# AI Context: IntentGuard

## Project Overview
* **Project Name**: IntentGuard
* **Description**: A macOS menu bar agent that monitors computer usage, compares it to a declared user goal, and uses AI to classify intent and intervene dynamically to prevent distraction.
* **Live URL**: TBD

## Technology Stack
* **Backend**: Python (FastAPI)
* **Screen Capturing**: `mss` (screenshot generation), `Pillow` (image downscaling and processing)
* **macOS Integration**: `pyobjc` (system API bindings), `pync` (system notifications)
* **Database**: SQLite (local session and activity storage)
* **Frontend/Dashboard**: React + Vite
* **AI Engine**: Gemini API (`google-genai` / `google-generativeai`) + Anthropic API

## Current Status
* **Phase**: Initial Setup & Architecture
* **Spike Prototype**: Validated. Screen capture loop using `mss` and classification using Gemini Flash successfully identifies `ON_TASK` and `OFF_TASK` states in real time from live screenshots.

## Architectural Notes
The application is structured into three clear, decoupled layers:
1. **Observer**: Captures system state (periodic screenshots, active window titles, process list).
2. **Brain**: Translates captured state + user intent into classification status (`ON_TASK`, `DRIFTING`, `BREAK`) via LLM API calls.
3. **Actor**: Triggers system-level intervention based on the Brain's classification and the configured aggressiveness slider.

## Next Milestones
1. Refactor the spike prototype into a reusable, structured `Brain` module.
2. Build the `Observer` module to monitor application names and window titles alongside screenshots.
3. Set up the local `SQLite` storage schema to track historical activity and logs.
4. Implement the `Actor` notifications and application-blocking rules.
