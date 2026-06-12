/* 全局工具 / Global utilities */

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(el, text) {
  if (!el || !text) return;
  if (typeof marked !== "undefined") {
    el.innerHTML = marked.parse(text);
  } else {
    el.textContent = text;
  }
}

async function api(method, url, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function showAlert(container, message, type = "warn") {
  const el = document.createElement("div");
  el.className = `alert alert-${type}`;
  el.textContent = message;
  container.prepend(el);
  setTimeout(() => el.remove(), 8000);
}

/* 全局搜索 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("global-search-form");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = document.getElementById("global-search-input").value.trim();
      const mode = document.getElementById("global-search-mode").value;
      if (!q) return;
      if (mode === "knowledge") {
        window.location.href = `/knowledge?q=${encodeURIComponent(q)}`;
      } else {
        window.location.href = `/?q=${encodeURIComponent(q)}`;
      }
    });
  }
});

/* 搜罗工作台 */
function initWorkspace(profiles, sources) {
  const form = document.getElementById("search-form");
  if (!form) return;

  const params = new URLSearchParams(window.location.search);
  const q = params.get("q");
  if (q) document.getElementById("search-query").value = q;

  checkAuthBanner();

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    await runSearch();
  });

  if (q) runSearch();
}

async function checkAuthBanner() {
  const banner = document.getElementById("auth-banner");
  if (!banner) return;
  try {
    const data = await api("GET", "/api/auth/status");
    const fails = data.items.filter((i) => !i.ok && (i.key === "zhihu" || i.key === "bilibili"));
    if (fails.length) {
      banner.classList.remove("hidden");
      banner.innerHTML = `部分来源未登录：${fails.map((f) => f.name).join("、")}。<a href="/settings">去设置同步 Cookie</a>`;
    }
  } catch (_) {}
}

async function runSearch() {
  const resultsEl = document.getElementById("search-results");
  const stepsEl = document.getElementById("steps-bar");
  const reportEl = document.getElementById("report-panel");
  const runLink = document.getElementById("run-link");

  resultsEl.innerHTML = "<p class='muted'>搜索中…</p>";
  stepsEl.innerHTML = "";
  if (reportEl) reportEl.innerHTML = "";

  const sources = [...document.querySelectorAll("input[name='sources']:checked")].map((el) => el.value);
  const body = {
    query: document.getElementById("search-query").value.trim(),
    sources,
    limit: parseInt(document.getElementById("search-limit").value, 10) || 10,
    digest: document.getElementById("opt-digest").checked,
    trace: document.getElementById("opt-trace").checked,
    profile: document.getElementById("search-profile").value,
    no_ai: document.getElementById("opt-no-ai").checked,
    no_simulate: document.getElementById("opt-no-simulate").checked,
    ai_instruct: document.getElementById("ai-instruct").value,
    deep_top: parseInt(document.getElementById("deep-top").value, 10) || 0,
    disabled_ai_steps: [...document.querySelectorAll("input[name='no-ai-step']:checked")].map((el) => el.value),
  };

  try {
    const { run_id } = await api("POST", "/api/search", body);
    runLink.href = `/runs/${run_id}`;
    runLink.classList.remove("hidden");
    runLink.textContent = `运行记录: ${run_id}`;

    subscribeSearchEvents(run_id, resultsEl, stepsEl, reportEl);
  } catch (err) {
    resultsEl.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
  }
}

function subscribeSearchEvents(runId, resultsEl, stepsEl, reportEl) {
  const seen = new Set();
  const es = new EventSource(`/api/search/${runId}/events`);

  es.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "step") {
      const step = msg.step?.step || msg.file;
      if (!seen.has(step)) {
        seen.add(step);
        const pill = document.createElement("span");
        pill.className = "step-pill done";
        pill.textContent = step;
        stepsEl.appendChild(pill);
      }
    }
    if (msg.type === "done") {
      es.close();
      renderSearchResults(msg.result, resultsEl, reportEl, runId);
    }
    if (msg.type === "error") {
      es.close();
      resultsEl.innerHTML = `<div class="alert alert-error">${escapeHtml(msg.error)}</div>`;
    }
  };

  es.onerror = () => {
    fetch(`/api/search/${runId}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.status === "done" && data.items) {
          es.close();
          renderSearchResults(data, resultsEl, reportEl, runId);
        }
      })
      .catch(() => {});
  };
}

function renderSearchResults(result, resultsEl, reportEl, runId) {
  const items = result.items || [];
  const sims = result.simulations || [];
  const simMap = {};
  sims.forEach((s) => { if (s.item_id) simMap[s.item_id] = s; });

  if (!items.length) {
    resultsEl.innerHTML = "<p class='muted'>未找到结果</p>";
    return;
  }

  resultsEl.innerHTML = items.map((item) => renderItemCard(item, simMap[item.id], runId)).join("");

  resultsEl.querySelectorAll("[data-feedback]").forEach((btn) => {
    btn.addEventListener("click", () => submitFeedback(btn.dataset.feedback, btn.dataset.id, runId));
  });
  resultsEl.querySelectorAll("[data-save]").forEach((btn) => {
    btn.addEventListener("click", () => saveFromCard(btn.dataset.save));
  });

  if (reportEl && result.report) {
    renderMarkdown(reportEl, result.report);
    initAskPanel(runId);
  }
}

function renderItemCard(item, sim, runId) {
  const fold = item.signals?.fold_reason
    ? `<div class="fold-reason">折叠原因: ${escapeHtml(item.signals.fold_reason)}</div>` : "";
  const simHtml = sim
    ? `<div class="layers"><strong>Persona 模拟:</strong> ${escapeHtml(sim.verdict || sim.summary || JSON.stringify(sim))}</div>` : "";
  const layers = [];
  if (item.summary) layers.push(`<p>${escapeHtml(item.summary)}</p>`);
  if (item.key_points?.length) layers.push(`<ul>${item.key_points.map((p) => `<li>${escapeHtml(p)}</li>`).join("")}</ul>`);
  if (item.layers?.comments) layers.push(`<details><summary>评论层</summary><pre>${escapeHtml(JSON.stringify(item.layers.comments, null, 2).slice(0, 2000))}</pre></details>`);

  return `<div class="card item-card">
    <div class="meta">[${escapeHtml(item.source)}] 相关度 ${item.signals?.relevance ?? "-"} | 营销嫌疑 ${item.signals?.marketing_suspect ?? "-"}</div>
    <div class="title">${escapeHtml(item.title)}</div>
    ${fold}
    <div class="layers">${layers.join("")}${simHtml}</div>
    <div class="actions">
      <a class="btn btn-sm" href="${escapeHtml(item.url)}" target="_blank">原文</a>
      <button class="btn btn-sm btn-secondary" data-save="${escapeHtml(item.url)}">收录</button>
      <button class="btn btn-sm btn-secondary" data-feedback="useful" data-id="${item.id}">有用</button>
      <button class="btn btn-sm btn-secondary" data-feedback="noise" data-id="${item.id}">噪音</button>
      <button class="btn btn-sm btn-secondary" data-feedback="entertainment" data-id="${item.id}">娱乐</button>
      <button class="btn btn-sm btn-danger" data-feedback="wrong" data-id="${item.id}">错误</button>
    </div>
  </div>`;
}

async function submitFeedback(rating, targetId, runId) {
  try {
    await api("POST", "/api/feedback", { target_id: targetId, rating, run_id: runId });
    alert("反馈已记录");
  } catch (err) {
    alert(err.message);
  }
}

async function saveFromCard(url) {
  try {
    const data = await api("POST", "/api/save", { url });
    alert(`已收录: ${data.item.title}`);
  } catch (err) {
    alert(err.message);
  }
}

function initAskPanel(runId) {
  const form = document.getElementById("ask-form");
  const history = document.getElementById("ask-history");
  if (!form) return;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const input = document.getElementById("ask-question");
    const q = input.value.trim();
    if (!q) return;
    try {
      const data = await api("POST", "/api/ask", { question: q, run_id: runId });
      const block = document.createElement("div");
      block.className = "card";
      block.innerHTML = `<p><strong>问:</strong> ${escapeHtml(q)}</p><div class="markdown-body"></div>`;
      renderMarkdown(block.querySelector(".markdown-body"), data.answer);
      history.appendChild(block);
      input.value = "";
    } catch (err) {
      alert(err.message);
    }
  };
}

/* 收录页 */
function initSave(prefillUrl) {
  const form = document.getElementById("save-form");
  if (!form) return;
  if (prefillUrl) document.getElementById("save-url").value = prefillUrl;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = document.getElementById("save-message");
    try {
      const data = await api("POST", "/api/save", {
        url: document.getElementById("save-url").value.trim(),
        with_comments: document.getElementById("save-comments").checked,
        no_ai: document.getElementById("save-no-ai").checked,
      });
      msg.className = "alert alert-success";
      msg.textContent = `已收录: ${data.item.title}`;
      loadRecentItems();
    } catch (err) {
      msg.className = "alert alert-error";
      msg.textContent = err.message;
    }
  });
  loadRecentItems();
}

async function loadRecentItems() {
  const el = document.getElementById("recent-items");
  if (!el) return;
  try {
    const data = await api("GET", "/api/knowledge/items?limit=10");
    el.innerHTML = data.items.map((i) =>
      `<div class="card"><a href="${escapeHtml(i.url)}" target="_blank">${escapeHtml(i.title)}</a><div class="muted">[${i.source}]</div></div>`
    ).join("") || "<p class='muted'>暂无收录</p>";
  } catch (_) {
    el.innerHTML = "<p class='muted'>加载失败</p>";
  }
}

/* 知识库 */
function initKnowledge() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get("q") || "";
  const input = document.getElementById("knowledge-query");
  if (input && q) input.value = q;
  const form = document.getElementById("knowledge-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      await searchKnowledge();
    });
    if (q) searchKnowledge();
  }
}

async function searchKnowledge() {
  const el = document.getElementById("knowledge-results");
  const q = document.getElementById("knowledge-query").value.trim();
  const source = document.getElementById("knowledge-source").value;
  let url = `/api/knowledge/items?q=${encodeURIComponent(q)}&limit=50`;
  if (source) url += `&source=${encodeURIComponent(source)}`;
  try {
    const data = await api("GET", url);
    el.innerHTML = data.items.map((i) =>
      `<div class="card item-card">
        <div class="meta">[${escapeHtml(i.source)}]</div>
        <div class="title">${escapeHtml(i.title)}</div>
        <p class="summary">${escapeHtml(i.summary || i.content?.slice(0, 200) || "")}</p>
        <a class="btn btn-sm" href="${escapeHtml(i.url)}" target="_blank">原文</a>
      </div>`
    ).join("") || "<p class='muted'>未找到匹配条目</p>";
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
  }
}

/* 简报 */
function initDigest() {
  document.getElementById("btn-daily")?.addEventListener("click", async () => {
    const el = document.getElementById("daily-content");
    el.innerHTML = "<p class='muted'>生成中…</p>";
    try {
      const data = await api("GET", "/api/digest/daily");
      renderMarkdown(el, data.content);
    } catch (err) {
      el.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
    }
  });
  loadReportList();
}

async function loadReportList() {
  const el = document.getElementById("report-list");
  if (!el) return;
  try {
    const data = await api("GET", "/api/digest/reports");
    el.innerHTML = `<table class="table"><thead><tr><th>Run ID</th><th>话题</th><th>操作</th></tr></thead><tbody>${
      data.reports.map((r) =>
        `<tr><td>${escapeHtml(r.run_id)}</td><td>${escapeHtml(r.query || "")}</td>
        <td><a href="/runs/${r.run_id}">详情</a></td></tr>`
      ).join("")
    }</tbody></table>` || "<p class='muted'>暂无历史报告</p>";
  } catch (_) {}
}

/* 画像 */
function initPersona() {
  loadPersona();
  document.getElementById("btn-build-persona")?.addEventListener("click", async () => {
    try {
      const data = await api("POST", "/api/persona/build?review=true");
      alert(`Persona v${data.version} 已生成`);
      loadPersona();
    } catch (err) { alert(err.message); }
  });
}

async function loadPersona() {
  const el = document.getElementById("persona-content");
  if (!el) return;
  try {
    const data = await api("GET", "/api/persona");
    const versions = (data.versions || []).map((v) => {
      const ver = v.replace("v", "");
      return `<button class="btn btn-sm btn-secondary" onclick="rollbackPersona(${ver})">回滚 ${v}</button>`;
    }).join(" ");
    el.innerHTML = `
      <div class="card"><h2>心智模型</h2><pre>${escapeHtml(JSON.stringify(data.mental_model, null, 2))}</pre></div>
      <div class="card"><h2>Brief</h2><div class="markdown-body" id="persona-brief"></div></div>
      <div class="mt-1">${versions}</div>`;
    renderMarkdown(document.getElementById("persona-brief"), data.brief || "（暂无）");
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
  }
}

async function rollbackPersona(version) {
  if (!confirm(`确认回滚到 v${version}？`)) return;
  try {
    const data = await api("POST", "/api/persona/rollback", { version });
    if (data.ok) { alert("回滚成功"); loadPersona(); }
    else alert("版本不存在");
  } catch (err) { alert(err.message); }
}

/* 导入 */
function initIngest() {
  document.getElementById("btn-ingest-browser")?.addEventListener("click", async () => {
    const days = parseInt(document.getElementById("browser-since").value, 10) || 90;
    await runIngest("browser", { since_days: days }, "ingest-browser-result");
  });
  document.getElementById("btn-ingest-bilibili")?.addEventListener("click", () =>
    runIngest("bilibili", null, "ingest-bilibili-result"));
  document.getElementById("btn-ingest-zhihu")?.addEventListener("click", () =>
    runIngest("zhihu", null, "ingest-zhihu-result"));
  loadLikes();
}

async function runIngest(type, body, resultId) {
  const el = document.getElementById(resultId);
  el.textContent = "导入中…";
  try {
    const url = type === "browser" ? "/api/ingest/browser" : `/api/ingest/${type}`;
    const data = await api("POST", url, body);
    el.className = "alert alert-success";
    el.textContent = `导入 ${data.count} 条。可到画像页重新构建。`;
  } catch (err) {
    el.className = "alert alert-error";
    el.textContent = err.message;
  }
}

async function loadLikes() {
  const el = document.getElementById("likes-list");
  if (!el) return;
  try {
    const data = await api("GET", "/api/ingest/likes");
    el.textContent = `认可记录: ${data.count} 条`;
  } catch (_) {}
}

/* 运行记录 */
function initRuns() {
  loadRunsList();
}

async function loadRunsList() {
  const el = document.getElementById("runs-list");
  if (!el) return;
  try {
    const data = await api("GET", "/api/runs?limit=50");
    el.innerHTML = `<table class="table"><thead><tr><th>Run ID</th><th>命令</th><th>话题</th></tr></thead><tbody>${
      data.runs.map((r) =>
        `<tr><td><a href="/runs/${r.run_id}">${escapeHtml(r.run_id)}</a></td>
        <td>${escapeHtml(r.command || "")}</td><td>${escapeHtml(r.query || "")}</td></tr>`
      ).join("")
    }</tbody></table>`;
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
  }
}

function initRunDetail(runId) {
  loadRunDetail(runId);
}

async function loadRunDetail(runId) {
  const el = document.getElementById("run-detail");
  if (!el) return;
  try {
    const data = await api("GET", `/api/runs/${runId}`);
    let html = `<div class="card"><h2>Manifest</h2><pre>${escapeHtml(JSON.stringify(data, null, 2).slice(0, 5000))}</pre></div>`;
    if (data.report) {
      html += `<div class="card"><h2>报告</h2><div class="markdown-body" id="run-report"></div></div>`;
    }
    if (data.artifacts?.length) {
      html += `<div class="card"><h2>Artifacts</h2><ul>${data.artifacts.map((a) =>
        `<li><a href="/api/runs/${runId}/artifacts/${a}" target="_blank">${escapeHtml(a)}</a></li>`
      ).join("")}</ul></div>`;
    }
    el.innerHTML = html;
    if (data.report) renderMarkdown(document.getElementById("run-report"), data.report);
  } catch (err) {
    el.innerHTML = `<div class="alert alert-error">${escapeHtml(err.message)}</div>`;
  }
}

/* AI 控制 */
function initAI() {
  loadDirectives();
  loadPromptList();
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.panel).classList.add("active");
    });
  });
  document.getElementById("btn-save-directives")?.addEventListener("click", saveDirectives);
  document.getElementById("btn-save-prompt")?.addEventListener("click", savePrompt);
  document.getElementById("btn-reset-prompt")?.addEventListener("click", resetPrompt);
  document.getElementById("prompt-select")?.addEventListener("change", loadPrompt);
}

async function loadDirectives() {
  const el = document.getElementById("directives-editor");
  const summary = document.getElementById("hard-constraints");
  if (!el) return;
  try {
    const data = await api("GET", "/api/ai/directives");
    el.value = JSON.stringify(data, null, 2);
    const hc = data.hard_constraints || data.get?.hard_constraints;
    if (summary && data.hard_constraints) {
      summary.textContent = `硬约束: ${JSON.stringify(data.hard_constraints)}`;
    }
  } catch (err) { el.value = err.message; }
}

async function saveDirectives() {
  try {
    const data = JSON.parse(document.getElementById("directives-editor").value);
    await api("PUT", "/api/ai/directives", { data });
    alert("已保存");
  } catch (err) { alert(err.message); }
}

async function loadPromptList() {
  const sel = document.getElementById("prompt-select");
  if (!sel) return;
  const data = await api("GET", "/api/ai/prompts");
  sel.innerHTML = data.prompts.map((p) =>
    `<option value="${p.name}">${p.name} (${p.source})</option>`
  ).join("");
  loadPrompt();
}

async function loadPrompt() {
  const name = document.getElementById("prompt-select").value;
  const data = await api("GET", `/api/ai/prompts/${name}`);
  document.getElementById("prompt-editor").value = data.text;
  document.getElementById("prompt-source").textContent = `来源: ${data.source}`;
}

async function savePrompt() {
  const name = document.getElementById("prompt-select").value;
  const text = document.getElementById("prompt-editor").value;
  await api("PUT", `/api/ai/prompts/${name}`, { text });
  alert("已保存");
  loadPromptList();
}

async function resetPrompt() {
  const name = document.getElementById("prompt-select").value;
  await api("POST", `/api/ai/prompts/${name}/reset`);
  alert("已恢复内置");
  loadPromptList();
}

/* 设置 */
function initSettings() {
  loadAuthStatus();
  loadPaths();
  document.getElementById("btn-sync-cookies")?.addEventListener("click", syncCookies);
  document.getElementById("btn-domain-lookup")?.addEventListener("click", lookupDomain);
}

async function loadAuthStatus() {
  const el = document.getElementById("auth-status");
  if (!el) return;
  try {
    const data = await api("GET", "/api/auth/status");
    el.innerHTML = `<table class="table"><thead><tr><th>项目</th><th>状态</th><th>说明</th></tr></thead><tbody>${
      data.items.map((i) =>
        `<tr><td>${escapeHtml(i.name)}</td>
        <td class="${i.ok ? "status-ok" : "status-fail"}">${i.ok ? "通过" : "失败"}</td>
        <td>${escapeHtml(i.detail || "")}</td></tr>`
      ).join("")
    }</tbody></table>`;
  } catch (err) {
    el.innerHTML = err.message;
  }
}

async function loadPaths() {
  const el = document.getElementById("paths-info");
  if (!el) return;
  const data = await api("GET", "/api/auth/paths");
  el.innerHTML = `<ul>
    <li>${escapeHtml(data.api_key_hint)}</li>
    <li>Cookie: ${escapeHtml(data.cookies_dir)}</li>
    <li>Data: ${escapeHtml(data.data_dir)}</li>
    <li>Directives: ${escapeHtml(data.directives_path)}</li>
  </ul>`;
}

async function syncCookies() {
  const el = document.getElementById("sync-result");
  el.textContent = "同步中…";
  try {
    const data = await api("POST", "/api/auth/sync-cookies", { browser: "edge" });
    el.className = "alert alert-success";
    el.textContent = `已同步: ${data.domains_synced.join(", ") || "无"}${data.errors.length ? " 错误: " + data.errors.join("; ") : ""}`;
    loadAuthStatus();
  } catch (err) {
    el.className = "alert alert-error";
    el.textContent = err.message;
  }
}

async function lookupDomain() {
  const domain = document.getElementById("domain-input").value.trim();
  const el = document.getElementById("domain-result");
  if (!domain) return;
  try {
    const data = await api("GET", `/api/tools/domain/${encodeURIComponent(domain)}`);
    el.innerHTML = `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
  } catch (err) {
    el.textContent = err.message;
  }
}
