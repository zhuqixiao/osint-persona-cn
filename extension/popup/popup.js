function setActionResult(text, kind = "") {
  const el = document.getElementById("action-result");
  if (!el) return;
  el.textContent = text || "";
  el.className = `action-result ${kind}`.trim();
}

async function loadStatus() {
  const enabledEl = document.getElementById("enabled");
  const passiveEl = document.getElementById("passive");
  const bgEl = document.getElementById("background-sync");
  const platformsEl = document.getElementById("platforms");
  const webEl = document.getElementById("web-status");
  const queueEl = document.getElementById("queue-status");

  const resp = await chrome.runtime.sendMessage({ kind: "get_status" });
  enabledEl.checked = resp.enabled !== false;
  passiveEl.checked = resp.passiveCollect !== false;
  bgEl.checked = resp.backgroundSync !== false;

  if (resp.webOnline) {
    webEl.className = "status-line ok";
    webEl.textContent = `Web 已连接 · v${resp.version || "?"} · ${resp.apiBase || ""}`;
  } else {
    webEl.className = "status-line fail";
    webEl.textContent = `Web 未连接：请先运行 osint web（8787）${resp.webError ? ` · ${resp.webError}` : ""}`;
  }

  const stats = resp.stats || {};
  const pending = resp.pendingQueue || 0;
  const parts = [];
  if (pending > 0) parts.push(`待上传 ${pending} 条`);
  if (resp.lastFlushError) parts.push(`上传失败：${resp.lastFlushError.slice(0, 80)}`);
  if (stats.lastFlush) parts.push(`上次上传 ${stats.lastFlush.slice(0, 19)}`);
  if (stats.lastAccepted != null && stats.lastFlush) parts.push(`写入 ${stats.lastAccepted}`);
  queueEl.textContent = parts.join(" · ") || "队列为空（正常）";
  queueEl.className = `status-line ${pending > 0 || resp.lastFlushError ? "warn" : "muted"}`;

  if (resp.platforms) {
    platformsEl.textContent = `覆盖: ${resp.platforms.join("、")}`;
  }
}

document.getElementById("enabled").addEventListener("change", async (e) => {
  await chrome.runtime.sendMessage({ kind: "set_enabled", enabled: e.target.checked });
  loadStatus();
});

document.getElementById("passive").addEventListener("change", async (e) => {
  await chrome.runtime.sendMessage({ kind: "set_passive", enabled: e.target.checked });
});

document.getElementById("background-sync").addEventListener("change", async (e) => {
  await chrome.runtime.sendMessage({ kind: "set_background_sync", enabled: e.target.checked });
});

document.getElementById("sync-cookies").addEventListener("click", async () => {
  setActionResult("从浏览器读取 Cookie 并写入本机…");
  const result = await chrome.runtime.sendMessage({ kind: "sync_cookies" });
  if (!result) {
    setActionResult("无响应：请重载扩展 v0.3.0+", "error");
    return;
  }
  if (result.error) {
    setActionResult(result.error, "error");
    return;
  }
  const synced = (result.domains_synced || []).join("、") || "无";
  setActionResult(`Cookie 已同步: ${synced}`, "success");
  loadStatus();
});

document.getElementById("flush").addEventListener("click", async () => {
  setActionResult("上传浏览采集队列…");
  const result = await chrome.runtime.sendMessage({ kind: "flush_now" });
  if (result.error) {
    let hint = "";
    if (/HTTP 5\d\d/i.test(result.error)) {
      hint = "（Web 已启动但处理出错，请重启情报台）";
    } else if (/fetch|failed|network|连接|refused|timeout/i.test(result.error)) {
      hint = "（请先运行 osint web）";
    }
    setActionResult(`失败: ${result.error}${hint}`, "error");
    loadStatus();
    return;
  }
  if (result.empty) {
    setActionResult("队列为空。日常浏览后会有数据，或等每分钟自动上传。", "success");
    loadStatus();
    return;
  }
  let msg = `上传完成：写入 ${result.accepted || 0}，跳过重复 ${result.skipped || 0}`;
  if (result.saved_to_knowledge) msg += `，知识库 ${result.saved_to_knowledge}`;
  setActionResult(msg, "success");
  loadStatus();
});

document.getElementById("sync-aicu").addEventListener("click", async () => {
  setActionResult("从 AICU 拉取发评中…");
  const result = await chrome.runtime.sendMessage({ kind: "sync_aicu" });
  if (!result) {
    setActionResult("无响应：请重载扩展 v0.3.0+", "error");
    return;
  }
  if (result.error) {
    setActionResult(result.error, "error");
    return;
  }
  if (result.ok === false) {
    setActionResult(result.error || "导入失败", "error");
    return;
  }
  setActionResult(`AICU 导入 ${result.count || 0} 条（跳过 ${result.skipped || 0}，UID ${result.mid || "?"})`, "success");
});

document.getElementById("sync-now").addEventListener("click", async () => {
  setActionResult("服务端 Cookie 拉取中…");
  let result;
  try {
    result = await chrome.runtime.sendMessage({ kind: "sync_now" });
  } catch (e) {
    setActionResult(`失败: ${e.message || e}`, "error");
    return;
  }
  if (!result) {
    setActionResult("无响应：请重载扩展后重试", "error");
    return;
  }
  if (result.error) {
    setActionResult(result.error, "error");
    return;
  }
  const bili = result?.stats?.server?.bilibili;
  const zh = result?.stats?.server?.zhihu;
  const parts = [];
  if (bili) {
    const d = [`B站 ${bili.count ?? 0}`];
    if (bili.following_count != null) d.push(`关注${bili.following_count}`);
    parts.push(d.join("/"));
  }
  if (zh) {
    const d = [`知乎 ${zh.count ?? 0}`];
    if (zh.activity_count != null) d.push(`动态${zh.activity_count}`);
    parts.push(d.join("/"));
  }
  if (result?.stats?.scroll?.pages) parts.push(`补洞 ${result.stats.scroll.pages} 页`);
  setActionResult(parts.length ? `拉取完成：${parts.join("，")}` : "拉取完成（0 条，请先同步 Cookie）", "success");
  loadStatus();
});

loadStatus();
