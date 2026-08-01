// Sesame Pass — popup: auto-detect browser, show connection status.
// No manual browser selector — guessBrowser() reads the UA and stores
// the result in storage so the background heartbeat uses the same value.

const browserInfoEl = document.getElementById("browser-info");
const statusEl      = document.getElementById("status");

function setStatus(text, ok) {
  statusEl.textContent = text;
  statusEl.className = ok ? "ok" : "err";
}

async function guessBrowser() {
  const ua = navigator.userAgent;
  if (ua.includes("Firefox/")) return "firefox";
  if (ua.includes("Edg/"))     return "edge";
  if (ua.includes("OPR/"))     return "opera";
  // Brave removes itself from the UA string — must use navigator.brave API.
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
  browserInfoEl.textContent = `Browser: ${browser}`;

  const response = await sendToBackground({ type: "ping", browser });
  setStatus(
    response && response.ok
      ? "Connected — Sesame is running."
      : "Sesame not detected — make sure it's running.",
    !!(response && response.ok)
  );
}

init();
