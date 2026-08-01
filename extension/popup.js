const titleEl      = document.getElementById("title");
const statusEl     = document.getElementById("status");
const statusTextEl = document.getElementById("status-text");

function capitalize(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function appVersion() {
  const v = chrome.runtime.getManifest().version; // e.g. "1.6.0"
  return "v" + v.replace(/\.0$/, "");             // → "v1.6"
}

async function guessBrowser() {
  const ua = navigator.userAgent;
  if (ua.includes("Firefox/")) return "firefox";
  if (ua.includes("Edg/"))     return "edge";
  if (ua.includes("OPR/"))     return "opera";
  if (navigator.brave && await navigator.brave.isBrave()) return "brave";
  return "chrome";
}

function sendToBackground(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) { resolve(null); return; }
      resolve(response);
    });
  });
}

async function init() {
  const browser = await guessBrowser();
  await chrome.storage.local.set({ browser });

  titleEl.textContent = `🔑 Sesame ${capitalize(browser)} Pass`;

  const response = await sendToBackground({ type: "ping", browser });
  const ok = !!(response && response.ok);

  statusEl.className = ok ? "ok" : "err";
  statusTextEl.textContent = ok
    ? "Connected"
    : `Disconnected - Open Sesame ${appVersion()}`;
}

init();
