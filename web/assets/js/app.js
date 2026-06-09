/** Turn Lab — live multi-turn demo via POST /v1/lab/turn */

const $ = (sel) => document.querySelector(sel);

const SUGGESTED = [
  "What should I ship today?",
  "Any blockers on my open PRs?",
  "Summarize my unread email",
  "What's the full picture across all my apps?",
];

let sessionId = "";
let turnCount = 0;
let running = false;

function apiPath(path) {
  const base = (window.SUPERCOMPRESS_API || "").replace(/\/$/, "");
  return base ? `${base}${path}` : path;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setStackActive(sponsor) {
  document.querySelectorAll(".lab-stack li").forEach((li) => {
    li.classList.toggle("active", li.dataset.sponsor === sponsor);
    li.classList.toggle("done", false);
  });
}

function markStackDone() {
  document.querySelectorAll(".lab-stack li").forEach((li) => {
    li.classList.add("done");
    li.classList.remove("active");
  });
}

function renderPhases(phases) {
  const log = $("#phase-log");
  if (!log) return;
  log.innerHTML = (phases || [])
    .map((p) => `<li><code>${escapeHtml(p.phase)}</code>${escapeHtml(p.detail)}</li>`)
    .join("");
  const last = phases?.[phases.length - 1];
  if (last) setStackActive(last.phase === "gather" ? "supercompress" : last.phase);
}

function renderTurnChart(history) {
  const el = $("#turn-chart");
  if (!el || !history?.length) {
    if (el) el.innerHTML = '<p class="dim">Run a turn to see context grow.</p>';
    return;
  }
  const max = Math.max(...history.map((t) => t.original_tokens), 1);
  el.innerHTML = history
    .map(
      (t) => `
    <div class="turn-row">
      <div class="turn-label">Turn ${t.turn}</div>
      <div class="turn-bars">
        <div class="bar-wrap">
          <span class="bar-label">Raw</span>
          <div class="bar-track"><div class="bar bar-raw" style="width:${(t.original_tokens / max) * 100}%"></div></div>
          <span class="bar-val">${t.original_tokens}</span>
        </div>
        <div class="bar-wrap">
          <span class="bar-label">Compressed</span>
          <div class="bar-track"><div class="bar bar-sc" style="width:${(t.compressed_tokens / max) * 100}%"></div></div>
          <span class="bar-val">${t.compressed_tokens} · ${t.kv_savings_pct}% saved</span>
        </div>
      </div>
    </div>`
    )
    .join("");
}

function renderStats(memory) {
  const panel = $("#stats-panel");
  const grid = $("#stats-grid");
  if (!panel || !grid || !memory) return;
  panel.hidden = false;
  grid.innerHTML = `
    <div class="stat"><span class="stat-n">${memory.original_tokens}</span><span class="stat-l">tokens in</span></div>
    <div class="stat"><span class="stat-n">${memory.kept_tokens}</span><span class="stat-l">kept</span></div>
    <div class="stat accent"><span class="stat-n">${memory.kv_savings_pct}%</span><span class="stat-l">KV saved</span></div>`;
}

function appendMessage(role, text, meta) {
  const thread = $("#chat-thread");
  if (!thread) return;
  const div = document.createElement("div");
  div.className = `lab-msg lab-msg--${role}`;
  div.innerHTML = `
    <span class="lab-avatar">${role === "user" ? "U" : "SC"}</span>
    <div class="lab-bubble">
      ${meta ? `<p class="lab-meta">${escapeHtml(meta)}</p>` : ""}
      <p>${escapeHtml(text)}</p>
    </div>`;
  thread.appendChild(div);
  thread.scrollTop = thread.scrollHeight;
}

function updateMeta(data) {
  turnCount = data.turn;
  const turnEl = $("#turn-num");
  const blockEl = $("#block-count");
  if (turnEl) turnEl.textContent = String(data.turn);
  const blocks = data.turn_history?.[data.turn_history.length - 1]?.blocks ?? 0;
  if (blockEl) blockEl.textContent = String(blocks);
  const input = $("#query-input");
  if (input && data.turn < 4) {
    input.placeholder = SUGGESTED[data.turn] || "Keep going — context is growing…";
  } else if (input) {
    input.placeholder = "Turn 4+ — this is where agents without compression die";
  }
}

async function runTurn(query) {
  if (running) return;
  running = true;
  const btn = $("#run-btn");
  const form = $("#lab-form");
  if (btn) btn.disabled = true;
  if (form) form.classList.add("loading");

  const q = query?.trim() || null;
  if (q) appendMessage("user", q);

  setStackActive("tavily");
  const phaseLog = $("#phase-log");
  if (phaseLog) phaseLog.innerHTML = "<li>Running sponsor stack…</li>";

  try {
    const r = await fetch(apiPath("/v1/lab/turn"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId || undefined,
        query: q,
        budget_ratio: 0.35,
      }),
    });
    if (!r.ok) {
      const err = await r.text();
      throw new Error(err || `HTTP ${r.status}`);
    }
    const data = await r.json();
    sessionId = data.session_id;
    markStackDone();
    renderPhases(data.phases);
    renderTurnChart(data.turn_history);
    renderStats(data.memory);
    updateMeta(data);

    const mem = data.memory;
    const meta = `Turn ${data.turn} · ${mem.original_tokens}→${mem.kept_tokens} tok · ${mem.kv_savings_pct}% KV saved`;
    appendMessage("agent", data.answer || "(no answer)", meta);

    if (data.turn === 4) {
      appendMessage(
        "agent",
        "Turn 4 — context would OOM without SuperCompress. Every prior turn's Tavily + Composio blocks are still in memory.",
        "Memory layer"
      );
    }
  } catch (e) {
    appendMessage("agent", `Lab unavailable: ${e.message}. API may be offline — start the stack locally.`, "Error");
    if (phaseLog) phaseLog.innerHTML = "";
  } finally {
    running = false;
    if (btn) btn.disabled = false;
    if (form) form.classList.remove("loading");
    const input = $("#query-input");
    if (input) input.value = "";
  }
}

function resetSession() {
  sessionId = "";
  turnCount = 0;
  const thread = $("#chat-thread");
  if (thread) thread.innerHTML = "";
  renderTurnChart([]);
  $("#stats-panel")?.setAttribute("hidden", "");
  $("#phase-log") && ($("#phase-log").innerHTML = "");
  document.querySelectorAll(".lab-stack li").forEach((li) => {
    li.classList.remove("active", "done");
  });
  const turnEl = $("#turn-num");
  const blockEl = $("#block-count");
  if (turnEl) turnEl.textContent = "0";
  if (blockEl) blockEl.textContent = "0";
  const input = $("#query-input");
  if (input) input.placeholder = SUGGESTED[0];
  appendMessage("agent", "Session reset. Run turn 1 — each turn adds Tavily search + Composio gather to accumulated context.", "Turn Lab");
}

async function loadStaticChart() {
  try {
    const r = await fetch(apiPath("/v1/turns/demo"));
    if (r.ok) {
      const d = await r.json();
      renderTurnChart(
        d.turns.map((t) => ({
          turn: t.turn,
          original_tokens: t.original_tokens,
          compressed_tokens: t.sc_tokens,
          kv_savings_pct: t.kv_savings_pct,
        }))
      );
      return true;
    }
  } catch (_) {}
  return false;
}

async function init() {
  renderTurnChart([]);
  appendMessage(
    "agent",
    "Welcome to Turn Lab. Hit Run turn — no API key needed. Each turn runs Tavily → Composio → SuperCompress → Nebius on all accumulated context.",
    "Ready"
  );

  $("#lab-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    runTurn($("#query-input")?.value);
  });
  $("#reset-btn")?.addEventListener("click", resetSession);

  const live = await fetch(apiPath("/v1/health")).then((r) => r.ok).catch(() => false);
  const badge = $("#mode-badge");
  if (badge) badge.textContent = live ? "Live API" : "API offline";
  if (!live) await loadStaticChart();

  const input = $("#query-input");
  if (input) input.placeholder = SUGGESTED[0];
}

init();
