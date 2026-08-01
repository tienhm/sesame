// Sesame Pass — popup: no pairing step anymore (Native Messaging trusts the
// extension by its pinned ID, see manifest.json's "key" + Sesame's registered
// host manifest). Just remember which browser this is (for Settings' status
// list) and show whether Sesame is reachable right now.

const browserSelect = document.getElementById("browser-select");
const statusEl = document.getElementById("status");

function setStatus(text, ok) {
  statusEl.textContent = text;
  statusEl.className = ok ? "ok" : "err";
}

function guessBrowser() {
  const ua = navigator.userAgent;
  if (ua.includes("Edg/")) return "edge";
  if (ua.includes("OPR/")) return "opera";
  if (ua.includes("Brave/")) return "brave";
  if (ua.includes("Firefox/")) return "firefox";
  return "chrome";
}

function sendToBackground(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        resolve(null);
        return;
      }
      resolve(response);
    });
  });
}

async function refreshStatus() {
  const response = await sendToBackground({ type: "ping", browser: browserSelect.value });
  setStatus(
    response && response.ok
      ? "Connected — Sesame is running."
      : "Sesame not detected — make sure it's running and the extension is installed correctly.",
    !!(response && response.ok)
  );
}

async function init() {
  const { browser } = await chrome.storage.local.get(["browser"]);
  browserSelect.value = browser || guessBrowser();
  await refreshStatus();
}

browserSelect.addEventListener("change", async () => {
  await chrome.storage.local.set({ browser: browserSelect.value });
  await refreshStatus();
});

init();
