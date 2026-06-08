/** SuperCompress demo app — works on GitHub Pages (static JSON) or live API */

const $ = (sel) => document.querySelector(sel);

async function loadDemo() {
  try {
    const r = await fetch("data/demo.json");
    if (r.ok) return r.json();
  } catch (_) {}
  try {
    const r = await fetch("/api/turns");
    if (r.ok) {
      const d = await r.json();
      return { turns: d.turns, query: d.query, sample: null };
    }
  } catch (_) {}
  return null;
}

function renderTurns(data) {
  const el = $("#turn-chart");
  if (!el || !data?.turns) return;
  const max = Math.max(...data.turns.map((t) => t.original_tokens));
  el.innerHTML = data.turns
    .map(
      (t) => `
    <div class="turn-row">
      <div class="turn-label">Turn ${t.turn}</div>
      <div class="turn-bars">
        <div class="bar-wrap">
          <span class="bar-label">Raw context</span>
          <div class="bar-track"><div class="bar bar-raw" style="width:${(t.original_tokens / max) * 100}%"></div></div>
          <span class="bar-val">${t.original_tokens} tok</span>
        </div>
        <div class="bar-wrap">
          <span class="bar-label">After SuperCompress</span>
          <div class="bar-track"><div class="bar bar-sc" style="width:${(t.sc_tokens / max) * 100}%"></div></div>
          <span class="bar-val">${t.sc_tokens} tok · ${t.kv_savings_pct}% saved</span>
        </div>
      </div>
    </div>`
    )
    .join("");
}

async function runCompress() {
  const context = $("#context-input")?.value || "";
  const query = $("#query-input")?.value || "What matters here?";
  const out = $("#compress-result");
  const btn = $("#compress-btn");
  if (!out) return;

  btn.disabled = true;
  out.textContent = "Compressing…";

  try {
    const r = await fetch("/api/compress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ context, query }),
    });
    if (r.ok) {
      const d = await r.json();
      showResult(d, out);
      btn.disabled = false;
      return;
    }
  } catch (_) {}

  const demo = await loadDemo();
  if (demo?.sample) {
    showResult(
      {
        original_tokens: demo.sample.original_tokens,
        kept_tokens: demo.sample.kept_tokens,
        fifo_tokens: demo.sample.fifo_tokens,
        kv_savings_pct: demo.sample.kv_savings_pct,
        policy: demo.sample.policy,
        compressed_preview: demo.sample.compressed_preview,
      },
      out
    );
    out.insertAdjacentHTML(
      "beforeend",
      '\n\n<span class="dim">(Static demo — run <code>./bin/supercompress serve</code> for live compression on your text)</span>'
    );
  } else {
    out.textContent = "Demo data unavailable.";
  }
  btn.disabled = false;
}

function showResult(d, out) {
  out.innerHTML = `
<div class="result-grid">
  <div class="stat"><span class="stat-n">${d.original_tokens}</span><span class="stat-l">tokens in</span></div>
  <div class="stat"><span class="stat-n">${d.kept_tokens}</span><span class="stat-l">tokens kept</span></div>
  <div class="stat accent"><span class="stat-n">${d.kv_savings_pct}%</span><span class="stat-l">KV saved</span></div>
</div>
<p class="result-meta">Policy: <strong>${d.policy || "SuperCompress"}</strong> · FIFO would keep ~${d.fifo_tokens} tokens</p>
<pre class="result-preview">${escapeHtml(d.compressed_preview || "")}</pre>`;
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function init() {
  const data = await loadDemo();
  renderTurns(data);

  if (data?.sample && $("#context-input")) {
    const sample = `## Tavily research
Composio shipped OpenClaw plugin. Nebius added Kimi K2.5.

---
## GitHub
- #42 fix/auth-timeout — review requested
- #39 feat/composio-triggers — draft

---
## Gmail
- sponsor@builders — Demo due June 12`;
    $("#context-input").value = sample;
    $("#query-input").value = data.sample.query || "What should I ship today?";
  }

  $("#compress-btn")?.addEventListener("click", runCompress);
  const live = await fetch("/api/health").then((r) => r.ok).catch(() => false);
  const badge = $("#mode-badge");
  if (badge) badge.textContent = live ? "Live API" : "Static demo";
}

init();
