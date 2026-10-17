import asyncio
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


class SlackDispatchError(RuntimeError):
    pass


async def dispatch_activity_to_go(
    session: dict,
    activity: dict,
    recent_context: list[dict],
) -> bool:
    token = os.environ.get("SLACK_USER_TOKEN")
    channel_id = os.environ.get("SLACK_CHANNEL_ID")
    if not token or not channel_id:
        print(
            "[GO] ERROR | Slack dispatch skipped: missing SLACK_USER_TOKEN or "
            "SLACK_CHANNEL_ID",
            flush=True,
        )
        return False

    message = build_intentguard_event(session, activity, recent_context)
    try:
        await asyncio.to_thread(
            _post_slack_message,
            token,
            channel_id,
            message,
        )
    except Exception as error:
        safe_error = str(error).replace(token, "[redacted]")
        print(f"[GO] ERROR | Slack dispatch failed: {safe_error}", flush=True)
        return False

    title = activity.get("title") or ""
    if len(title) > 80:
        title = f"{title[:77]}..."
    print(
        f"[GO] DISPATCH | event={activity['eventId']} | "
        f"{activity.get('domain') or '-'} | {title}",
        flush=True,
    )
    return True


def build_intentguard_event(
    session: dict,
    activity: dict,
    recent_context: list[dict],
) -> str:
    duration = activity.get("durationSeconds", 0)
    if isinstance(duration, float) and duration.is_integer():
        duration = int(duration)

    lines = [
        "INTENTGUARD_EVENT",
        "",
        f"Event ID: {activity['eventId']}",
        f"Session ID: {session['id']}",
        f"Goal: {session['goal']}",
        "",
        "Current activity:",
        f"Domain: {activity.get('domain') or '-'}",
        f"Title: {activity.get('title') or '-'}",
        f"URL: {activity.get('url') or '-'}",
        f"Duration: {duration} seconds",
    ]

    recent_lines = _recent_activity_lines(recent_context)
    if recent_lines:
        lines.extend(["", "Recent activity:", *recent_lines])

    return "\n".join(lines)


def _recent_activity_lines(recent_context: list[dict]) -> list[str]:
    completed = [
        event
        for event in recent_context
        if event.get("event_type") == "activity_end"
        and event.get("durationSeconds") is not None
    ][-3:]
    return [
        f"- {event.get('domain') or '-'} | {event.get('title') or '-'} | "
        f"{event['durationSeconds']}s"
        for event in completed
    ]


def _post_slack_message(token: str, channel_id: str, message: str) -> None:
    request = Request(
        SLACK_POST_MESSAGE_URL,
        data=json.dumps({"channel": channel_id, "text": message}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            response_body = json.load(response)
    except HTTPError as error:
        raise SlackDispatchError(f"Slack returned HTTP {error.code}") from None
    except URLError as error:
        raise SlackDispatchError(f"Slack network error: {error.reason}") from None

    if not response_body.get("ok"):
        error_code = response_body.get("error", "unknown_error")
        raise SlackDispatchError(f"Slack API error: {error_code}")
