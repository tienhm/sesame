// Sesame Pass — content script: on click/focus of a username/password field,
// offer to fill it from a matching Sesame entry. Field-mapping (which input
// on this domain is username vs password) is learned and kept entirely in
// chrome.storage.local — Sesame's backend never sees it.
//
// The browser's own built-in password manager also reacts to focus on these
// same fields and shows its native "choose saved password" dropdown, which
// visually competes with (and can render on top of / block) our own
// suggestion UI. Two mitigations, matching what other password-manager
// extensions do:
//   1. On first encountering a field, mark autocomplete "off"/"new-password"
//      and briefly toggle `readonly` on focus — a well-known best-effort
//      trick that suppresses Chrome's native suggestion dropdown for that
//      focus event. Not 100% guaranteed (browsers keep tightening this), but
//      meaningfully reduces collisions.
//   2. Don't show our own suggestion panel automatically on focus at all —
//      only show a small inline badge (so we never race the browser's
//      autofill popup for the same screen space); the full suggestion list
//      only opens when the user deliberately clicks that badge.

(() => {
  const FILLABLE_TYPES = new Set(["text", "email", "password", "tel", "", null]);
  const PING_CACHE_MS = 10_000;      // don't re-check liveness on every focus
  const PORT_SCAN_COUNT = 20;        // matches Sesame's own bind-scan range
  const FIRST_PORT = 37821;

  let tooltipEl = null;
  let badgeEl = null;
  let badgeForEl = null;
  const handledFields = new WeakSet();
  let lastLivenessCheck = 0;
  let cachedLiveness = null;   // { paired: bool, running: bool, port: number|null }

  function isFillableInput(el) {
    if (!(el instanceof HTMLInputElement)) return false;
    return FILLABLE_TYPES.has((el.getAttribute("type") || "").toLowerCase());
  }

  function fieldKeyFor(el) {
    if (el.name) return `name:${el.name}`;
    if (el.id) return `id:${el.id}`;
    const all = Array.from(document.querySelectorAll("input"));
    return `idx:${all.indexOf(el)}`;
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

  async function pingPort(port, timeoutMs = 800) {
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), timeoutMs);
      const resp = await fetch(`http://127.0.0.1:${port}/ping`, { signal: ctrl.signal });
      clearTimeout(timer);
      return resp.ok;
    } catch (e) {
      return false;
    }
  }

  // Not paired yet: we don't know Sesame's port, so probe the same range
  // Sesame itself scans when binding. Only used to decide silent vs.
  // "please pair" — never used to read data (that always requires the code).
  async function probeAnyRunning() {
    const ports = Array.from({ length: PORT_SCAN_COUNT }, (_, i) => FIRST_PORT + i);
    const results = await Promise.all(ports.map((p) => pingPort(p, 500)));
    return results.some(Boolean);
  }

  async function checkLiveness() {
    const now = Date.now();
    if (cachedLiveness && now - lastLivenessCheck < PING_CACHE_MS) {
      return cachedLiveness;
    }
    lastLivenessCheck = now;

    const { code, port } = await chrome.storage.local.get(["code", "port"]);
    if (code && port) {
      const running = await pingPort(port);
      cachedLiveness = { paired: true, running, port };
    } else {
      const running = await probeAnyRunning();
      cachedLiveness = { paired: false, running, port: null };
    }
    return cachedLiveness;
  }

  function removeTooltip() {
    if (tooltipEl) {
      tooltipEl.remove();
      tooltipEl = null;
    }
  }

  function removeBadge() {
    if (badgeEl) {
      badgeEl.remove();
      badgeEl = null;
      badgeForEl = null;
    }
  }

  function removeOverlays() {
    removeTooltip();
    removeBadge();
  }

  function positionBadge(el) {
    const rect = el.getBoundingClientRect();
    badgeEl.style.top = `${rect.top + Math.max(0, (rect.height - 18) / 2)}px`;
    badgeEl.style.left = `${rect.right - 22}px`;
  }

  // Small inline icon anchored to the field's own position — shown on focus
  // instead of the full suggestion list, so we never fight the browser's
  // native dropdown for the same spot. Clicking it opens the real menu.
  function showBadge(el) {
    if (badgeForEl === el) {
      positionBadge(el); // already showing for this field — just realign
      return;
    }
    removeBadge();
    badgeEl = document.createElement("div");
    badgeForEl = el;
    badgeEl.textContent = "🔑";
    badgeEl.title = "Sesame Pass";
    badgeEl.style.cssText = `
      position: fixed;
      width: 18px;
      height: 18px;
      z-index: 2147483647;
      cursor: pointer;
      font-size: 12px;
      line-height: 18px;
      text-align: center;
      background: #25262f;
      border: 1px solid #3a3b47;
      border-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.4);
    `;
    positionBadge(el);
    // mousedown + preventDefault (not click) so the input never loses focus
    // when the badge is pressed.
    badgeEl.addEventListener("mousedown", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      onBadgeActivated(el);
    });
    document.body.appendChild(badgeEl);
  }

  function showTooltip(anchor, contentBuilder) {
    removeTooltip();
    const rect = anchor.getBoundingClientRect();
    tooltipEl = document.createElement("div");
    tooltipEl.style.cssText = `
      position: fixed;
      top: ${rect.bottom + 4}px;
      left: ${rect.left}px;
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

  async function fillField(el, entryId, field, port, code) {
    try {
      const resp = await fetch(`http://127.0.0.1:${port}/reveal`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${code}`,
        },
        body: JSON.stringify({ entry_id: entryId, field }),
      });
      if (resp.status === 401) {
        warningTooltip(el, "Pairing key changed — re-pair in the extension popup");
        return;
      }
      if (resp.status === 423) {
        warningTooltip(el, "That entry is locked in Sesame — unlock it there first");
        return;
      }
      if (!resp.ok) return;
      const data = await resp.json();
      setNativeValue(el, data.value || "");
      removeTooltip();
    } catch (e) {
      // Sesame went away mid-request — fail silently, matches the
      // "not running" = silent rule.
    }
  }

  async function saveMapping(domain, fieldKey, field) {
    const { fieldMap } = await chrome.storage.local.get(["fieldMap"]);
    const map = fieldMap || {};
    map[domain] = map[domain] || {};
    map[domain][fieldKey] = field;
    await chrome.storage.local.set({ fieldMap: map });
  }

  async function getMapping(domain, fieldKey) {
    const { fieldMap } = await chrome.storage.local.get(["fieldMap"]);
    return fieldMap?.[domain]?.[fieldKey];
  }

  // Triggered by a deliberate click on the inline badge — this is where the
  // actual liveness/pairing/entries logic runs, well after the browser's own
  // focus-triggered autofill dropdown has already had its chance to appear.
  async function onBadgeActivated(el) {
    const liveness = await checkLiveness();

    if (!liveness.running) {
      removeTooltip();
      return;
    }

    if (!liveness.paired) {
      warningTooltip(el, "Please pair with Sesame — open the extension popup");
      return;
    }

    const { code, port } = await chrome.storage.local.get(["code", "port"]);
    const domain = location.hostname;

    let entries;
    try {
      const resp = await fetch(
        `http://127.0.0.1:${port}/entries?domain=${encodeURIComponent(domain)}`,
        { headers: { Authorization: `Bearer ${code}` } }
      );
      if (resp.status === 401) {
        warningTooltip(el, "Pairing key changed — re-pair in the extension popup");
        return;
      }
      if (!resp.ok) return;
      ({ entries } = await resp.json());
    } catch (e) {
      return; // Sesame vanished between the ping and this call — silent.
    }

    if (!entries || entries.length === 0) {
      removeTooltip();
      return;
    }

    const fieldKey = fieldKeyFor(el);
    const known = await getMapping(domain, fieldKey);

    showTooltip(el, (root) => {
      entries.forEach((entry) => {
        const row = document.createElement("div");
        row.style.cssText = "display:flex; gap:4px; align-items:center; margin:2px 0;";
        const label = document.createElement("span");
        label.textContent = entry.name;
        label.style.cssText = "flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;";
        row.appendChild(label);

        const elType = (el.getAttribute("type") || "text").toLowerCase();
        let fieldsToOffer;
        if (known) {
          fieldsToOffer = [known];
        } else if (elType === "password") {
          fieldsToOffer = ["password"];
        } else if (entry.has_username) {
          fieldsToOffer = ["username", "password"]; // ambiguous text field — let user pick, remembered next time
        } else {
          fieldsToOffer = ["password"];
        }
        fieldsToOffer.forEach((field) => {
          const btn = document.createElement("button");
          btn.textContent = field === "username" ? "👤" : "🔑";
          btn.title = `Fill ${field}`;
          btn.style.cssText =
            "cursor:pointer; background:#5865f2; color:#fff; border:none; border-radius:4px; padding:2px 6px;";
          btn.addEventListener("mousedown", async (ev) => {
            ev.preventDefault(); // keep the field focused
            ev.stopPropagation();
            await saveMapping(domain, fieldKey, field);
            await fillField(el, entry.id, field, port, code);
          });
          row.appendChild(btn);
        });
        root.appendChild(row);
      });
    });
  }

  document.addEventListener(
    "focusin",
    (ev) => {
      if (isFillableInput(ev.target)) {
        suppressNativeAutofill(ev.target);
        showBadge(ev.target);
      }
    },
    true
  );

  document.addEventListener("focusout", (ev) => {
    const target = ev.target;
    if (target !== badgeForEl) return;
    // Small delay so a mousedown on the badge/tooltip isn't dismissed by the
    // input losing focus first (the badge/tooltip buttons already call
    // preventDefault on mousedown to avoid this, but scroll/other blur
    // sources are still handled here). Re-check badgeForEl at fire time —
    // tabbing straight to the next fillable field already reassigned it to
    // that field's badge, which must survive.
    setTimeout(() => {
      if (badgeForEl === target) removeOverlays();
    }, 150);
  });

  // Keep the badge aligned with its field across scrolling/resizing while
  // it's shown; cheap since it only runs while a badge exists.
  const reposition = () => {
    if (badgeForEl) showBadge(badgeForEl);
  };
  window.addEventListener("scroll", reposition, true);
  window.addEventListener("resize", reposition);
})();
