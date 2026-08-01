// Sesame Pass — popup: paste the pairing code shown in Sesame Settings →
// Extensions once, decode it locally to find the port, and store the code
// (unchanged) + port + browser identity for background.js/content_script.js.

const codeInput = document.getElementById("code-input");
const browserSelect = document.getElementById("browser-select");
const pairBtn = document.getElementById("pair-btn");
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

async function pingPort(port) {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const resp = await fetch(`http://127.0.0.1:${port}/ping`, { signal: ctrl.signal });
    clearTimeout(timer);
    return resp.ok;
  } catch (e) {
    return false;
  }
}

async function loadExisting() {
  const { code, port, browser } = await chrome.storage.local.get(["code", "port", "browser"]);
  browserSelect.value = browser || guessBrowser();
  if (code && port) {
    codeInput.value = code;
    const alive = await pingPort(port);
    setStatus(alive ? `Paired — Sesame is running on port ${port}.`
                     : `Paired, but Sesame is not reachable on port ${port}.`, alive);
  } else {
    browserSelect.value = guessBrowser();
    setStatus("Not paired yet.", false);
  }
}

pairBtn.addEventListener("click", async () => {
  const raw = codeInput.value.trim();
  if (!raw) {
    setStatus("Paste a pairing code first.", false);
    return;
  }
  let decoded;
  try {
    decoded = atob(raw);
  } catch (e) {
    setStatus("That doesn't look like a valid pairing code (bad base64).", false);
    return;
  }
  const sep = decoded.lastIndexOf(":");
  if (sep === -1) {
    setStatus("That doesn't look like a valid pairing code (missing port).", false);
    return;
  }
  const port = parseInt(decoded.slice(sep + 1), 10);
  if (!Number.isInteger(port) || port <= 0) {
    setStatus("That doesn't look like a valid pairing code (bad port).", false);
    return;
  }

  const browser = browserSelect.value;
  await chrome.storage.local.set({ code: raw, port, browser });

  const alive = await pingPort(port);
  setStatus(
    alive
      ? `Paired! Sesame is running on port ${port}.`
      : `Saved, but couldn't reach Sesame on port ${port} — make sure it's running.`,
    alive
  );
});

loadExisting();
