import asyncio
import subprocess

from brain.evaluator import Decision


async def send_nudge(goal: str, decision: Decision) -> None:
    """Send one local macOS notification without invoking a shell."""
    message = f"You said you wanted to: {goal}"
    script = (
        'on run argv\n'
        'display notification (item 1 of argv) with title "IntentGuard" '
        'subtitle "Still intentional?"\n'
        'end run'
    )
    await asyncio.to_thread(
        subprocess.run,
        ["osascript", "-e", script, "--", message],
        check=True,
        capture_output=True,
        text=True,
    )
