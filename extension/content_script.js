// Sesame Pass — content script: on double-click of a username/password
// field, offer to fill it from a matching Sesame entry.
//
// Trigger is double-click, not focus. A plain focus/single-click already
// makes the browser's own built-in password manager show its native
// "choose saved password" dropdown on many sites, which visually competes
// with (and can render on top of / block) our own suggestion UI. Focus
// happens on every tab-through or click; double-click is a distinct,
// deliberate action that doesn't fire on ordinary navigation, so it mostly
// sidesteps that collision (not a full fix — the native dropdown is outside
// our control and can still appear from the plain click half of the
// double-click — just a pragmatic reduction).
//
// Each matching entry offers ONE guessed button by default — 👤 for a
// plain text-like field, 🔑 for a field whose current `type` attribute is
// "password" — same guess as before. That guess can be wrong: many sites
// put their own show/hide toggle on the password field, which flips
// `type="password"` -> `type="text"` when revealed, so a field that is
// still, semantically, the password field can look like a plain text field
// by the time you interact with it again. Escape hatch: while the tooltip
// is open, holding Shift reveals the *other* button for every row too, so
// you can force-paste the field the guess got wrong — live, with nothing
// remembered between visits (no chrome.storage.local field-mapping cache
// anymore; this replaces that).
//
// All communication with Sesame goes through the background service worker
// (Native Messaging — see background.js) via chrome.runtime.sendMessage;
// content scripts can't call chrome.runtime.connectNative directly. There's
// no more pairing code/port/bearer-token to track here — "liveness" is just
// "did the background relay get a response at all".
//
// suppressNativeAutofill() (below) stays focus-triggered, independent of
// the double-click tooltip trigger — it's a best-effort attempt to preempt
// the browser's native dropdown, and has to run on the very first focus,
// before that dropdown would otherwise appear.

(() => {
  const FILLABLE_TYPES = new Set(["text", "email", "password", "tel", "", null]);
  const PING_CACHE_MS = 10_000;      // don't re-check liveness on every double-click

  let tooltipEl = null;
  let tooltipForEl = null;
  const handledFields = new WeakSet();
  let lastLivenessCheck = 0;
  let cachedLiveness = null;   // { running: bool }
  let shiftKeyHandler = null;
  let outsideClickHandler = null;
  let escapeKeyHandler = null;

  function isFillableInput(el) {
    if (!(el instanceof HTMLInputElement)) return false;
    return FILLABLE_TYPES.has((el.getAttribute("type") || "").toLowerCase());
  }

  // Best-effort suppression of the browser's own native suggestion dropdown
  // for this field — see file header. Applied once per element.
  function suppressNativeAutofill(el) {
    if (handledFields.has(el)) return;
    handledFields.add(el);

    const elType = (el.getAttribute("type") || "text").toLowerCase();
    el.setAttribute("autocomplete", elType === "password" ? "new-password" : "off");

    el.addEventListener("focus", () => {
      el.setAttribute("readonly", "readonly");
      setTimeout(() => el.removeAttribute("readonly"), 10);
    });
  }

  // Relays a request to the background service worker, which owns the
  // actual Native Messaging connection to Sesame (see background.js).
  // Resolves to null — never rejects — if Sesame/the relay is unreachable,
  // so every caller can treat "no response" as "not running".
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

  async function checkLiveness() {
    const now = Date.now();
    if (cachedLiveness && now - lastLivenessCheck < PING_CACHE_MS) {
      return cachedLiveness;
    }
    lastLivenessCheck = now;
    const response = await sendToBackground({ type: "ping" });
    cachedLiveness = { running: !!(response && response.ok) };
    return cachedLiveness;
  }

  // While the tooltip is open, Shift reveals every row's hidden "other"
  // button (see buildEntryRows); released, they hide again. Scoped to the
  // tooltip's lifetime — attached in showTooltip(), detached in
  // removeTooltip() — so there's no page-global Shift listener sitting
  // around when no tooltip exists.
  function attachShiftReveal() {
    shiftKeyHandler = (ev) => {
      if (ev.key !== "Shift" || !tooltipEl) return;
      const shifted = ev.type === "keydown";
      tooltipEl.querySelectorAll('[data-shift-reveal="1"]').forEach((btn) => {
        btn.style.display = shifted ? "inline-block" : "none";
      });
      tooltipEl.querySelectorAll('[data-shift-primary="1"]').forEach((btn) => {
        btn.style.display = shifted ? "none" : "inline-block";
      });
    };
    document.addEventListener("keydown", shiftKeyHandler);
    document.addEventListener("keyup", shiftKeyHandler);
  }

  function detachShiftReveal() {
    if (!shiftKeyHandler) return;
    document.removeEventListener("keydown", shiftKeyHandler);
    document.removeEventListener("keyup", shiftKeyHandler);
    shiftKeyHandler = null;
  }

  // Dismiss on a click outside the tooltip/anchor field, or on Escape.
  // Replaces the old focus-tied dismissal, which no longer maps cleanly to
  // "user is done" now that showing is double-click-triggered rather than
  // focus-triggered (the field stays focused after a fill, and
  // double-clicking an already-focused field doesn't refire focus).
  function attachDismissListeners() {
    outsideClickHandler = (ev) => {
      if (tooltipEl && !tooltipEl.contains(ev.target) && ev.target !== tooltipForEl) {
        removeTooltip();
      }
    };
    escapeKeyHandler = (ev) => {
      if (ev.key === "Escape" && tooltipEl) removeTooltip();
    };
    document.addEventListener("mousedown", outsideClickHandler, true);
    document.addEventListener("keydown", escapeKeyHandler);
  }

  function detachDismissListeners() {
    if (outsideClickHandler) {
      document.removeEventListener("mousedown", outsideClickHandler, true);
      outsideClickHandler = null;
    }
    if (escapeKeyHandler) {
      document.removeEventListener("keydown", escapeKeyHandler);
      escapeKeyHandler = null;
    }
  }

  function removeTooltip() {
    detachShiftReveal();
    detachDismissListeners();
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
      tooltipForEl = null;
    }
  }

  function positionTooltip(el) {
    const rect = el.getBoundingClientRect();
    tooltipEl.style.top = `${rect.bottom + 4}px`;
    tooltipEl.style.left = `${rect.left}px`;
  }

  function showTooltip(anchor, contentBuilder) {
    removeTooltip();
    tooltipEl = document.createElement("div");
    tooltipForEl = anchor;
    tooltipEl.style.cssText = `
      position: fixed;
      z-index: 2147483647;
      background: #25262f;
      color: #e8eaed;
      border: 1px solid #3a3b47;
      border-radius: 6px;
      padding: 6px;
      font: 12px "Segoe UI", sans-serif;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      max-width: 260px;
    `;
    contentBuilder(tooltipEl);
    document.body.appendChild(tooltipEl);
    positionTooltip(anchor);
    attachShiftReveal();
    attachDismissListeners();
  }

  function warningTooltip(anchor, message) {
    showTooltip(anchor, (el) => {
      el.textContent = `⚠ ${message}`;
    });
  }

  function setNativeValue(el, value) {
    // Bypasses React/Vue's overridden value setter so controlled inputs pick
    // up the change (plain el.value = ... is swallowed by the framework).
    const proto = Object.getPrototypeOf(el);
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) {
      setter.call(el, value);
    } else {
      el.value = value;
    }
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  async function fillField(el, entryId, field) {
    const response = await sendToBackground({ type: "reveal", entry_id: entryId, field, domain: location.hostname });
    if (!response) return; // Sesame went away mid-request — fail silently.
    if (response.error === "locked") {
      warningTooltip(el, "That entry is locked in Sesame — unlock it there first");
      return;
    }
    if (response.error) return; // not_found/invalid_field — nothing sensible to show.
    setNativeValue(el, response.value || "");
    removeTooltip();
  }

  // One row per matching entry. Each row gets its guessed button (based on
  // the field's current `type`, same heuristic as before) visible right
  // away, plus the other button hidden — only shown while Shift is held
  // (see attachShiftReveal). Never offer a hidden 👤 button for an entry
  // with no username.
  function buildEntryRows(root, el, entries) {
    const elType = (el.getAttribute("type") || "text").toLowerCase();

    entries.forEach((entry) => {
      const row = document.createElement("div");
      row.style.cssText = "display:flex; gap:4px; align-items:center; margin:2px 0;";
      const label = document.createElement("span");
      label.textContent = entry.name;
      label.style.cssText = "flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;";
      row.appendChild(label);

      let guessed;
      if (elType === "password") {
        guessed = "password";
      } else if (entry.has_username) {
        guessed = "username";
      } else {
        guessed = "password";
      }
      const other = guessed === "username" ? "password" : "username";

      const makeButton = (field, hiddenByDefault) => {
        const btn = document.createElement("button");
        btn.textContent = field === "username" ? "👤" : "🔑";
        btn.title = `Fill ${field}`;
        btn.style.cssText =
          "cursor:pointer; background:#5865f2; color:#fff; border:none; border-radius:4px; padding:2px 6px;" +
          (hiddenByDefault ? " display:none;" : "");
        if (hiddenByDefault) btn.dataset.shiftReveal = "1";
        else btn.dataset.shiftPrimary = "1";
        btn.addEventListener("mousedown", async (ev) => {
          ev.preventDefault(); // keep the field focused
          ev.stopPropagation();
          await fillField(el, entry.id, field);
        });
        return btn;
      };

      const primaryBtn = makeButton(guessed, false);
      row.appendChild(primaryBtn);
      const hasSecondary = other !== "username" || entry.has_username;
      if (hasSecondary) {
        row.appendChild(makeButton(other, true));
      } else {
        // No secondary button exists — don't mark primary as shift-swappable
        // or Shift will hide the only button with nothing to replace it.
        delete primaryBtn.dataset.shiftPrimary;
      }
      root.appendChild(row);
    });
  }

  async function onFieldActivate(el) {
    const liveness = await checkLiveness();

    if (!liveness.running) {
      removeTooltip();
      return;
    }

    const domain = location.hostname;
    const response = await sendToBackground({ type: "entries", domain });
    const entries = response && response.entries;

    if (!entries || entries.length === 0) {
      removeTooltip();
      return;
    }

    showTooltip(el, (root) => buildEntryRows(root, el, entries));
  }

  document.addEventListener(
    "focusin",
    (ev) => {
      if (isFillableInput(ev.target)) {
        suppressNativeAutofill(ev.target);
      }
    },
    true
  );

  document.addEventListener(
    "dblclick",
    (ev) => {
      if (isFillableInput(ev.target)) {
        onFieldActivate(ev.target);
      }
    },
    true
  );

  // Keep the tooltip aligned with its field across scrolling/resizing while
  // it's shown; cheap since it only runs while a tooltip exists.
  const reposition = () => {
    if (tooltipForEl) positionTooltip(tooltipForEl);
  };
  window.addEventListener("scroll", reposition, true);
  window.addEventListener("resize", reposition);
})();
