// Sesame Pass — background service worker.
//
// Talks to Sesame via Native Messaging instead of HTTP loopback: no more
// `fetch` to 127.0.0.1, no more Private Network Access permission prompts.
// Chrome/Edge spawn a fresh native-host process (see native_host.py in the
// repo, built as its own exe) per `connectNative()` call, keyed to this
// extension's pinned ID (see manifest.json's "key") via the host manifest
// registered by Sesame on startup — no pairing code to copy/paste anymore.
//
// content_script.js and popup.js can't call connectNative directly (that
// permission is background-script-only) — they relay requests here via
// chrome.runtime.sendMessage, and this file does the actual native call.

const NATIVE_HOST_NAME = "com.sesame.pass";
const ALARM_NAME = "sesame-heartbeat";
const NATIVE_TIMEOUT_MS = 3000;

// Sends exactly one message over a fresh native connection and resolves with
// the one response — mirrors the old single fetch()-per-request model, so
// callers don't have to deal with connectNative's persistent-port semantics
// or correlate concurrent requests on one port. Resolves to null (not a
// rejection) when Sesame is unreachable — every caller already treats "no
// response" as "not running", same as the old fetch-failed case.
function nativeRequest(message) {
  return new Promise((resolve) => {
    let settled = false;
    let port;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        port && port.disconnect();
      } catch (e) {
        // already disconnected — fine.
      }
      resolve(result);
    };

    const timer = setTimeout(() => finish(null), NATIVE_TIMEOUT_MS);

    try {
      port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
    } catch (e) {
      finish(null);
      return;
    }

    port.onMessage.addListener((response) => finish(response));
    port.onDisconnect.addListener(() => {
      // Reading chrome.runtime.lastError marks it "checked" — Sesame not
      // running yet (native host manifest not registered, or the process
      // can't reach the pipe) disconnects the port with lastError set to
      // something like "Specified native messaging host not found.". Not
      // reading it here makes Chrome auto-log "Unchecked runtime.lastError"
      // to the console on every failed attempt, which is exactly the spam
      // this fixes — this is the expected "Sesame isn't up" case, not a
      // real error, so it's deliberately swallowed rather than logged.
      void chrome.runtime.lastError;
      finish(null);
    });

    try {
      port.postMessage(message);
    } catch (e) {
      finish(null);
    }
  });
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  nativeRequest(message).then(sendResponse);
  return true; // keep the message channel open for the async response
});

// MV3 service workers are non-persistent (suspended after ~30s idle), so a
// plain setInterval would stop firing once the worker is unloaded. chrome.alarms
// survives worker suspension, but Chrome clamps alarm periods below 1 minute
// to 1 minute for published extensions (unpacked/dev-mode builds can go as low
// as 15s in older Chrome versions). We ask for 0.25 min (15s) — Chrome silently
// clamps it as needed — and the Sesame-side heartbeat timeout (90s) tolerates
// the worst case (~60s) without flapping the "Connected" indicator.
chrome.alarms.create(ALARM_NAME, { periodInMinutes: 0.25 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) sendHeartbeat();
});

// Also ping once immediately when the worker (re)starts, instead of waiting
// for the first alarm tick.
sendHeartbeat();

async function sendHeartbeat() {
  const { browser } = await chrome.storage.local.get(["browser"]);
  await nativeRequest({ type: "ping", browser: browser || guessBrowser() });
}

function guessBrowser() {
  const ua = navigator.userAgent;
  if (ua.includes("Edg/")) return "edge";
  if (ua.includes("OPR/")) return "opera";
  if (ua.includes("Brave/")) return "brave";
  if (ua.includes("Firefox/")) return "firefox";
  return "chrome";
}
