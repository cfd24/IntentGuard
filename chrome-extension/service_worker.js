const STATE_KEY = "intentguard_current_activity";
const ACTIVITY_ENDPOINT = "http://127.0.0.1:8000/activity";

function nowIso() {
  return new Date().toISOString();
}

function domainFromUrl(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

async function getCurrentActivity() {
  const result = await chrome.storage.local.get(STATE_KEY);
  return result[STATE_KEY] || null;
}

async function setCurrentActivity(activity) {
  await chrome.storage.local.set({
    [STATE_KEY]: activity,
  });
}

async function postActivityEvent(event) {
  try {
    const response = await fetch(ACTIVITY_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(event),
    });

    if (!response.ok) {
      console.warn(
        `[IntentGuard] Backend rejected activity event (${response.status}).`,
      );
    }
  } catch (error) {
    console.warn("[IntentGuard] Backend unavailable; observation continues.", error);
  }
}

async function observeTab(tab, reason) {
  if (!tab || !tab.active) return;

  if (!tab.url || tab.url.startsWith("chrome://")) {
    return;
  }

  const previous = await getCurrentActivity();
  const timestamp = nowIso();
  let endedActivity = null;

  if (
    previous &&
    (previous.tabId !== tab.id ||
      previous.url !== tab.url ||
      previous.title !== tab.title)
  ) {
    const durationMs =
      Date.now() - new Date(previous.startedAt).getTime();

    endedActivity = {
      ...previous,
      event_type: "activity_end",
      timestamp,
      endedAt: timestamp,
      durationSeconds: Math.round(durationMs / 1000),
    };

    console.log("[IntentGuard] ACTIVITY_END", endedActivity);
  }

  const sameActivity =
    previous &&
    previous.tabId === tab.id &&
    previous.url === tab.url &&
    previous.title === tab.title;

  if (sameActivity) return;

  const activity = {
    tabId: tab.id,
    windowId: tab.windowId,
    url: tab.url,
    domain: domainFromUrl(tab.url),
    title: tab.title || "",
    startedAt: timestamp,
    reason,
  };

  await setCurrentActivity(activity);

  console.log("[IntentGuard] ACTIVITY_START", activity);

  // Persist and log first so a slow/offline backend cannot interrupt observation.
  if (endedActivity) {
    await postActivityEvent(endedActivity);
  }
  await postActivityEvent({
    ...activity,
    event_type: "activity_start",
    timestamp,
  });
}

chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  try {
    const tab = await chrome.tabs.get(tabId);
    await observeTab(tab, "tab_activated");
  } catch (error) {
    console.error("[IntentGuard] onActivated error:", error);
  }
});

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (!tab.active) return;

  if (changeInfo.url || changeInfo.title) {
    try {
      await observeTab(tab, "tab_updated");
    } catch (error) {
      console.error("[IntentGuard] onUpdated error:", error);
    }
  }
});

chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;

  try {
    const tabs = await chrome.tabs.query({
      active: true,
      windowId,
    });

    if (tabs[0]) {
      await observeTab(tabs[0], "window_focused");
    }
  } catch (error) {
    console.error("[IntentGuard] window focus error:", error);
  }
});

console.log("[IntentGuard] Observer service worker loaded.");
