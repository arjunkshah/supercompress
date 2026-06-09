/** Ship Brief — consumer product (Tavily + Composio + SuperCompress + Nebius) */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const TOKEN_KEY = "sc_token";
let useFirebase = false;

function apiPath(path) {
  const base = (window.SUPERCOMPRESS_API || "").replace(/\/$/, "");
  return base ? `${base}${path}` : path;
}

async function authHeaders() {
  let t = localStorage.getItem(TOKEN_KEY) || "";
  if (useFirebase && window.ScFirebase?.ready) {
    t = (await ScFirebase.getIdToken(true)) || t;
    if (t) localStorage.setItem(TOKEN_KEY, t);
  }
  return { Authorization: `Bearer ${t}`, "Content-Type": "application/json", "ngrok-skip-browser-warning": "1" };
}

async function api(method, path, body) {
  const opts = { method, headers: await authHeaders() };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(apiPath(path), opts);
  const text = await r.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { throw new Error("API offline"); }
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Request failed");
  return data;
}

function show(el) { el?.classList.remove("hidden"); }
function hide(el) { el?.classList.add("hidden"); }

function setView(id) {
  hide($("#auth-gate"));
  hide($("#connect-gate"));
  hide($("#brief-app"));
  show($(`#${id}`));
}

async function loadConnectGrid() {
  const el = $("#connect-grid");
  try {
    const data = await api("GET", "/v1/dashboard/integrations");
    const linked = new Set(data.linked || []);
    el.innerHTML = ["github", "gmail"].map((tk) => {
      const on = linked.has(tk);
      const label = tk === "github" ? "GitHub" : "Gmail";
      return `<div class="brief-connect-row">
        <span>${label}</span>
        ${on ? '<span class="int-connected-badge">Connected</span>' : `<button type="button" class="btn btn-pear btn-sm connect-btn" data-tk="${tk}">Connect</button>`}
      </div>`;
    }).join("");
    $$(".connect-btn", el).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const res = await api("POST", `/v1/dashboard/integrations/connect/${btn.dataset.tk}`);
        if (res.redirect_url) window.open(res.redirect_url, "_blank");
      });
    });
    if (["github", "gmail"].some((tk) => linked.has(tk))) setView("brief-app");
  } catch (e) {
    el.innerHTML = `<p class="auth-error">${e.message}</p>`;
  }
}

function animatePipeline() {
  const steps = $$(".brief-step");
  const order = ["tavily", "composio", "compress", "nebius"];
  let i = 0;
  steps.forEach((s) => s.classList.remove("active", "done"));
  const tick = () => {
    steps.forEach((s) => s.classList.add("done"));
    const step = steps.find((s) => s.dataset.step === order[i]);
    if (step) { step.classList.remove("done"); step.classList.add("active"); }
    i += 1;
    if (i < order.length) setTimeout(tick, 900);
  };
  tick();
}

async function generateBrief() {
  const btn = $("#generate-btn");
  btn.disabled = true;
  show($("#brief-loading"));
  hide($("#brief-output"));
  hide($("#brief-stats"));
  animatePipeline();
  try {
    const data = await api("POST", "/v1/brief/generate");
    const m = data.memory || {};
    $("#brief-stats").innerHTML = `
      <div class="brief-stat"><span class="brief-stat-n">${m.original_tokens ?? "—"}</span><span class="brief-stat-l">tokens gathered</span></div>
      <div class="brief-stat"><span class="brief-stat-n">${m.kept_tokens ?? "—"}</span><span class="brief-stat-l">after compress</span></div>
      <div class="brief-stat"><span class="brief-stat-n">${Number(m.kv_savings_pct || 0).toFixed(0)}%</span><span class="brief-stat-l">KV saved</span></div>`;
    $("#brief-output").textContent = data.answer || "";
    show($("#brief-stats"));
    show($("#brief-output"));
    $$(".brief-step").forEach((s) => { s.classList.remove("active"); s.classList.add("done"); });
  } catch (e) {
    alert(e.message);
  } finally {
    hide($("#brief-loading"));
    btn.disabled = false;
  }
}

async function syncSession(user) {
  const t = await user.getIdToken();
  localStorage.setItem(TOKEN_KEY, t);
  await api("GET", "/v1/dashboard/me");
  const data = await api("GET", "/v1/dashboard/integrations");
  const linked = (data.linked || []).length;
  if (linked > 0) setView("brief-app");
  else { setView("connect-gate"); loadConnectGrid(); }
}

async function init() {
  $("#brief-date").textContent = new Date().toLocaleDateString(undefined, {
    weekday: "long", month: "long", day: "numeric",
  });
  $("#generate-btn")?.addEventListener("click", generateBrief);
  $("#refresh-connect")?.addEventListener("click", loadConnectGrid);

  const baked = window.SUPERCOMPRESS_FIREBASE;
  if (baked?.enabled) {
    useFirebase = true;
    show($("#google-signin-btn"));
    await ScFirebase.init(baked);
    $("#google-signin-btn")?.addEventListener("click", () => ScFirebase.signInWithGoogle());
    ScFirebase.onAuthStateChanged(async (user) => {
      if (!user) { setView("auth-gate"); return; }
      try { await syncSession(user); } catch (e) {
        $("#auth-error").textContent = e.message;
        show($("#auth-error"));
      }
    });
    return;
  }
  setView("auth-gate");
}

init();
