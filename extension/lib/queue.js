const EventQueue = {
  _key: "pendingEvents",
  _maxAttempts: 3,
  async enqueue(event) {
    if (event.kind === "page_visit" && EventQueue._shouldSkipVisit(event.url)) {
      return;
    }
    const items = await EventQueue._load();
    items.push({ ...event, ts: Date.now() });
    if (items.length > 500) items.splice(0, items.length - 500);
    await EventQueue._save(items);
    EventQueue._updateBadge(items.length);
    if (items.length >= 20) {
      await EventQueue.flush();
    }
  },
  _shouldSkipVisit(url) {
    if (!url) return true;
    const now = Date.now();
    const key = String(url).split("#")[0];
    if (!EventQueue._recentVisits) EventQueue._recentVisits = new Map();
    const prev = EventQueue._recentVisits.get(key);
    if (prev && now - prev < 45000) return true;
    EventQueue._recentVisits.set(key, now);
    if (EventQueue._recentVisits.size > 200) {
      for (const [k, ts] of EventQueue._recentVisits) {
        if (now - ts > 120000) EventQueue._recentVisits.delete(k);
      }
    }
    return false;
  },
  async pendingCount() {
    const items = await EventQueue._load();
    return items.length;
  },
  _sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  },
  _updateBadge(pending, hasError = false) {
    try {
      if (hasError && pending > 0) {
        chrome.action.setBadgeText({ text: String(Math.min(pending, 99)) });
        chrome.action.setBadgeBackgroundColor({ color: "#dc2626" });
        return;
      }
      if (pending > 0) {
        chrome.action.setBadgeText({ text: String(Math.min(pending, 99)) });
        chrome.action.setBadgeBackgroundColor({ color: "#d97706" });
        return;
      }
      chrome.action.setBadgeText({ text: "" });
    } catch (_) {}
  },
  async flush() {
    const items = await EventQueue._load();
    if (!items.length) {
      EventQueue._updateBadge(0);
      return { accepted: 0, skipped: 0, empty: true, pending: 0 };
    }
    const apiBase = await OSINTConfig.getApiBase();
    let lastErr = "";
    for (let attempt = 0; attempt < EventQueue._maxAttempts; attempt += 1) {
      try {
        const resp = await fetch(`${apiBase}/api/extension/events`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            events: items,
            version: OSINTConfig.extVersion,
          }),
        });
        if (!resp.ok) {
          let detail = `HTTP ${resp.status}`;
          try {
            const errBody = await resp.json();
            if (errBody.detail) {
              detail = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
            }
          } catch (_) {}
          throw new Error(detail);
        }
        const result = await resp.json();
        await EventQueue._save([]);
        const stats = {
          lastFlush: new Date().toISOString(),
          lastAccepted: result.accepted || 0,
          lastSkipped: result.skipped || 0,
        };
        await EventQueue._setStorage({ stats, lastFlushError: "" });
        EventQueue._updateBadge(0);
        return { ...result, empty: false, pending: 0 };
      } catch (err) {
        lastErr = String(err.message || err);
        if (attempt < EventQueue._maxAttempts - 1) {
          await EventQueue._sleep(800 * (attempt + 1));
        }
      }
    }
    await EventQueue._setStorage({ lastFlushError: lastErr });
    EventQueue._updateBadge(items.length, true);
    return { error: lastErr, pending: items.length };
  },
  _setStorage(patch) {
    return new Promise((resolve) => {
      chrome.storage.local.set(patch, resolve);
    });
  },
  _load() {
    return new Promise((resolve) => {
      chrome.storage.local.get([EventQueue._key], (data) => {
        resolve(Array.isArray(data[EventQueue._key]) ? data[EventQueue._key] : []);
      });
    });
  },
  _save(items) {
    return new Promise((resolve) => {
      chrome.storage.local.set({ [EventQueue._key]: items }, resolve);
    });
  },
};
