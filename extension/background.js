// Sesame Pass — background service worker: periodic heartbeat to Sesame.
//
// MV3 service workers are non-persistent (suspended after ~30s idle), so a
// plain setInterval would stop firing once the worker is unloaded. chrome.alarms
// survives worker suspension, but Chrome clamps alarm periods below 1 minute
// to 1 minute for published extensions (unpacked/dev-mode builds can go as low
// as 15s in older Chrome versions). We ask for 0.25 min (15s) — Chrome silently
// clamps it as needed — and the Sesame-side heartbeat timeout (90s) tolerates
// the worst case (~60s) without flapping the "Connected" indicator.

const ALARM_NAME = "sesame-heartbeat";

chrome.alarms.create(ALARM_NAME, { periodInMinutes: 0.25 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    sendHeartbeat();
  }
});

// Also ping once immediately when the worker (re)starts, instead of waiting
// for the first alarm tick.
sendHeartbeat();

async function sendHeartbeat() {
  const { code, port, browser } = await chrome.storage.local.get(["code", "port", "browser"]);
  if (!code || !port) return;   // not paired yet — nothing to report

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 3000);
    await fetch(`http://127.0.0.1:${port}/ping`, {
      method: "POST",
      signal: ctrl.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ browser: browser || "chrome" }),
    });
    clearTimeout(timer);
  } catch (e) {
    // Sesame not running / port unreachable — silently skip, next alarm retries.
  }
}
