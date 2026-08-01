// Sesame Pass — content script: on focus of a username/password field, offer
// to fill it from a matching Sesame entry. Field-mapping (which input on
// this domain is username vs password) is learned and kept entirely in
// chrome.storage.local — Sesame's backend never sees it.
//
// The browser's own built-in password manager also reacts to focus on these
// same fields and shows its native "choose saved password" dropdown, which
// visually competes with (and can render on top of / block) our own
// suggestion UI. Best-effort mitigation only (per explicit product decision —
// showing the picker immediately on focus matters more than dodging this
// collision): on first encountering a field, mark autocomplete
// "off"/"new-password" and briefly toggle `readonly` on focus, a well-known
// trick that suppresses the native suggestion dropdown for that focus event.
// Not 100% guaranteed (browsers keep tightening this) and does not fully
// eliminate the collision.

(() => {
  const FILLABLE_TYPES = new Set(["text", "email", "password", "tel", "", null]);
  const PING_CACHE_MS = 10_000;      // don't re-check liveness on every focus
  const PORT_SCAN_COUNT = 20;        // matches Sesame's own bind-scan range
  const FIRST_PORT = 37821;

  let tooltipEl = null;
  let tooltipForEl = null;
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

  // Runs directly on focus — liveness/pairing check first (cached, see
  // checkLiveness) so most focuses resolve instantly, then shows the
  // suggestion tooltip right away per product decision (see file header for
  // the native-dropdown collision tradeoff this accepts).
  async function onFieldFocus(el) {
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
        onFieldFocus(ev.target);
      }
    },
    true
  );

  document.addEventListener("focusout", (ev) => {
    const target = ev.target;
    if (target !== tooltipForEl) return;
    // Small delay so a mousedown on the tooltip's fill buttons isn't
    // dismissed by the input losing focus first (those buttons already call
    // preventDefault on mousedown to avoid this, but scroll/other blur
    // sources are still handled here). Re-check tooltipForEl at fire time —
    // tabbing straight to the next fillable field already reassigned it to
    // that field's tooltip, which must survive.
    setTimeout(() => {
      if (tooltipForEl === target) removeTooltip();
    }, 150);
  });

  // Keep the tooltip aligned with its field across scrolling/resizing while
  // it's shown; cheap since it only runs while a tooltip exists.
  const reposition = () => {
    if (tooltipForEl) positionTooltip(tooltipForEl);
  };
  window.addEventListener("scroll", reposition, true);
  window.addEventListener("resize", reposition);
})();
