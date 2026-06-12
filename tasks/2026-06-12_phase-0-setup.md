# Task: Convert spike.py into clean brain module

## TASK ID
`2026-06-12-phase-0-setup`

## TASK NAME
Convert spike.py into clean brain module

## STATUS
todo

## PHASE
Phase 0

## GOAL
Extract the screen capture and LLM classification logic from `spike.py` and convert it into a clean, reusable, and testable `Brain` module in the `brain/` directory.

## CONTEXT
Currently, `spike.py` is a single script containing prompt engineering, screen capture, PIL processing, and API configuration. In accordance with `AGENTS.md`, we must separate the concerns. The brain module should expose a simple interface: `classify(screenshot: PIL.Image.Image, goal: str) -> dict` returning status and reason.

## STEPS
- [ ] Initialize the `brain/` directory structure with `__init__.py` and a core module (e.g., `brain/classifier.py`).
- [ ] Implement `classify(screenshot: PIL.Image.Image, goal: str) -> dict` returning `{"status": "ON_TASK" | "OFF_TASK", "reason": str}`.
- [ ] Integrate API keys from an environment config file or system environment variable, defaulting to standard `GEMINI_API_KEY`.
- [ ] Maintain robust fallback mechanisms for Gemini models (`gemini-3.5-flash`, `gemini-2.5-flash`).
- [ ] Create a lightweight test script `brain/test_brain.py` that takes a sample screenshot, runs the classifier, and asserts the output structure.

## EXPECTED OUTPUT
A modular `brain/` python package that can be imported elsewhere in the engine (`from brain.classifier import classify`) and executed cleanly without hardcoded configuration.

## BLOCKERS
None
