/** SuperCompress developer dashboard */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const TOKEN_KEY = "sc_token";
const API_KEY_KEY = "sc_api_key";
let useFirebase = false;
let sessionSyncing = null;
let currentFirebaseUser = null;
let lastSyncedUid = null;
let creatingKey = false;
let pgRunning = false;
let pgPhaseTimer = null;

const DEFAULT_PG_TASKS = ["Ship onboarding flow", "Fix reminder timezone bug"];
const DEFAULT_PG_REMINDERS = ["Call dentist Tuesday 3pm"];

function apiPath(path) {
  const base = (window.SUPERCOMPRESS_API || "").replace(/\/$/, "");
  return base ? `${base}${path}` : path;
}

function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

async function authHeaders() {
  let t = token();
  if (useFirebase && window.ScFirebase?.ready) {
    t = (await ScFirebase.getIdToken(true)) || t;
    if (t) localStorage.setItem(TOKEN_KEY, t);
  }
  return { Authorization: `Bearer ${t}`, "Content-Type": "application/json" };
}

async function fetchJson(method, path, body, headers = {}) {
  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "1",
      ...headers,
    },
  };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(apiPath(path), opts);
  const text = await r.text();
  let data = null;
  if (text) {
    const trimmed = text.trim();
    if (trimmed.startsWith("<")) {
      throw new Error(
        "API backend is offline (got HTML instead of JSON). Keep the local API + ngrok tunnel running, or deploy to Render."
      );
    }
    try {
      data = JSON.parse(text);
    } catch {
      if (r.ok) {
        throw new Error("API returned invalid JSON. The backend may be offline.");
      }
      data = {};
    }
  }
  if (r.ok && (data === null || typeof data !== "object" || Array.isArray(data))) {
    throw new Error("API returned an unexpected response.");
  }
  const payload = data || {};
  const detail =
    typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail || "");
  if (!r.ok) throw new Error(detail || r.statusText || "Request failed");
  return payload;
}

async function api(method, path, body) {
  return fetchJson(method, path, body, await authHeaders());
}

function setHeaderUser(user) {
  const name = user.name || user.email?.split("@")[0] || "Account";
  const email = user.email || "";
  const initial = (name.charAt(0) || email.charAt(0) || "A").toUpperCase();
  const photo = currentFirebaseUser?.photoURL || user.photoURL || "";
  const nameEl = $("#header-user-name");
  const emailEl = $("#header-user-email");
  const initialEl = $("#header-user-initial");
  const photoEl = $("#header-user-photo");
  if (nameEl) nameEl.textContent = name;
  if (emailEl) emailEl.textContent = email;
  if (initialEl) initialEl.textContent = initial;
  if (photo && photoEl) {
    photoEl.src = photo;
    photoEl.classList.remove("hidden");
    initialEl?.classList.add("hidden");
  } else {
    photoEl?.classList.add("hidden");
    initialEl?.classList.remove("hidden");
  }
  $("#dash-profile")?.classList.remove("hidden");
}

function showAuth() {
  $("#auth-screen")?.classList.remove("hidden");
  $("#dash-screen")?.classList.add("hidden");
  $("#logout-btn")?.classList.add("hidden");
  $("#logout-btn-mobile")?.classList.add("hidden");
  $("#dash-profile")?.classList.add("hidden");
}

function isApiOfflineError(err) {
  const msg = err?.message || "";
  return (
    msg.includes("offline") ||
    msg.includes("invalid JSON") ||
    msg.includes("Failed to fetch") ||
    msg.includes("NetworkError") ||
    msg.includes("unexpected response")
  );
}

function showAuthError(message) {
  const el = $("#auth-error");
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
}

function hideAuthError() {
  $("#auth-error")?.classList.add("hidden");
}

function setApiOfflineBanner(show) {
  const existing = $("#api-offline-banner");
  if (!show) {
    existing?.remove();
    return;
  }
  if (existing) return;
  const banner = document.createElement("div");
  banner.id = "api-offline-banner";
  banner.className = "dash-offline-banner";
  banner.setAttribute("role", "status");
  banner.textContent =
    "API backend is offline — keys, integrations, and playground need the server running.";
  $(".dash-main")?.prepend(banner);
}

function profileFromFirebase(fbUser) {
  return {
    id: fbUser.uid || "",
    name: fbUser.displayName || "",
    email: fbUser.email || "",
  };
}

function resolveDashboardUser(data, fbUser) {
  const apiUser = data?.user;
  if (apiUser && (apiUser.id || apiUser.email)) return apiUser;
  if (fbUser) return profileFromFirebase(fbUser);
  return null;
}

function showDash(user) {
  if (!user) {
    showAuth();
    showAuthError("Signed in but could not load your profile. Refresh or try again.");
    return false;
  }
  $("#auth-screen")?.classList.add("hidden");
  $("#dash-screen")?.classList.remove("hidden");
  $("#dash-profile")?.classList.remove("hidden");
  $("#logout-btn-mobile")?.classList.remove("hidden");
  setHeaderUser(user);
  loadOverview();
  loadKeys();
  loadIntegrations();
  initPlayground();
  const saved = localStorage.getItem(API_KEY_KEY);
  if (saved && $("#pg-key")) $("#pg-key").value = saved;
  return true;
}

function setView(name) {
  $$(".dash-nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $$(".dash-view").forEach((v) => v.classList.add("hidden"));
  $(`#view-${name}`)?.classList.remove("hidden");
}

function fmtTime(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function fmtNum(n) {
  return Number(n || 0).toLocaleString();
}

const TOOLKIT_LABELS = {
  gmail: "Gmail",
  github: "GitHub",
  linear: "Linear",
  slack: "Slack",
  googlecalendar: "Google Calendar",
};

const TOOLKIT_ICONS = {
  gmail: { slug: "gmail", color: "EA4335" },
  github: { slug: "github", color: "181717" },
  linear: { slug: "linear", color: "5E6AD2" },
  slack: { slug: "slack", color: "4A154B" },
  googlecalendar: { slug: "googlecalendar", color: "4285F4" },
};

function toolkitLogo(id) {
  const icon = TOOLKIT_ICONS[id];
  if (icon) {
    const src = `https://cdn.simpleicons.org/${icon.slug}/${icon.color}`;
    return `<img class="int-logo-img" src="${src}" alt="" width="24" height="24" loading="lazy" decoding="async" />`;
  }
  return `<img class="int-logo-img" src="https://cdn.simpleicons.org/composio/000000" alt="" width="24" height="24" loading="lazy" />`;
}

function toolkitLabel(id) {
  return TOOLKIT_LABELS[id] || id.charAt(0).toUpperCase() + id.slice(1);
}

function renderPgList(listEl, items, listId) {
  if (!listEl) return;
  listEl.innerHTML = items
    .map(
      (text, i) => `<li class="pg-item">
        <span>${escapeHtml(text)}</span>
        <button type="button" class="pg-item-remove" data-list="${listId}" data-index="${i}" aria-label="Remove">×</button>
      </li>`
    )
    .join("");
  $$(".pg-item-remove", listEl).forEach((btn) => {
    btn.addEventListener("click", () => {
      const arr = getPgList(btn.dataset.list);
      arr.splice(Number(btn.dataset.index), 1);
      setPgList(btn.dataset.list, arr);
    });
  });
}

function getPgList(id) {
  const key = `pg_${id}`;
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) return JSON.parse(raw);
  } catch (_) {
    /* ignore */
  }
  return id === "tasks" ? [...DEFAULT_PG_TASKS] : [...DEFAULT_PG_REMINDERS];
}

function setPgList(id, items) {
  sessionStorage.setItem(`pg_${id}`, JSON.stringify(items));
  renderPgList($(`#pg-${id}`), items, id);
}

function initPlayground() {
  renderPgList($("#pg-tasks"), getPgList("tasks"), "tasks");
  renderPgList($("#pg-reminders"), getPgList("reminders"), "reminders");
}

function buildContextBlocks() {
  const tasks = getPgList("tasks");
  const reminders = getPgList("reminders");
  const blocks = [];
  if (tasks.length) blocks.push(`## User tasks\n${tasks.map((t) => `- ${t}`).join("\n")}`);
  if (reminders.length) blocks.push(`## Reminders\n${reminders.map((r) => `- ${r}`).join("\n")}`);
  return blocks;
}

function addPgItem(listId, inputId) {
  const input = $(inputId);
  const val = input?.value?.trim();
  if (!val) return;
  const items = getPgList(listId);
  items.push(val);
  setPgList(listId, items);
  if (input) input.value = "";
}

const PG_PHASES = ["Tavily", "Composio", "SuperCompress", "Nebius"];

function showPgRunning(out) {
  out.innerHTML = `<div class="pg-running">
    <div class="pg-spinner" aria-hidden="true"></div>
    <p class="pg-running-label">Running agent turn…</p>
    <div class="pg-phase-track" id="pg-phase-track">${PG_PHASES.map((p, i) =>
      `<span class="pg-phase${i === 0 ? " active" : ""}">${p}</span>`
    ).join("")}</div>
  </div>`;
  let step = 0;
  clearInterval(pgPhaseTimer);
  pgPhaseTimer = setInterval(() => {
    step = (step + 1) % PG_PHASES.length;
    $$(".pg-phase", out).forEach((el, i) => el.classList.toggle("active", i === step));
  }, 1400);
}

function stopPgRunning() {
  clearInterval(pgPhaseTimer);
  pgPhaseTimer = null;
}

function setPgRunning(running) {
  pgRunning = running;
  const btn = $("#pg-run");
  if (btn) {
    btn.disabled = running;
    btn.textContent = running ? "Running…" : "Run agent turn";
    btn.setAttribute("aria-busy", running ? "true" : "false");
  }
  $$(".pg-form input, .pg-form button:not(#pg-run)").forEach((el) => {
    if (el.id !== "pg-run") el.disabled = running;
  });
}

async function loadOverview() {
  try {
    const data = await api("GET", "/v1/dashboard/usage");
    const t = data.totals || {};
    $("#stat-requests").textContent = fmtNum(t.requests);
    $("#stat-tokens-in").textContent = fmtNum(t.original_tokens);
    $("#stat-tokens-out").textContent = fmtNum(t.kept_tokens);
    $("#stat-savings").textContent = `${Number(t.avg_savings || 0).toFixed(1)}%`;

    const recent = data.recent || [];
    const el = $("#recent-table");
    if (!recent.length) {
      el.innerHTML = '<p class="dash-empty">No requests yet. Create a key and call the API.</p>';
      return;
    }
    el.innerHTML = `<table class="data-table">
      <thead><tr><th>Time</th><th>Key</th><th>Endpoint</th><th>In</th><th>Kept</th><th>Saved</th></tr></thead>
      <tbody>${recent
        .map(
          (r) => `<tr>
        <td>${fmtTime(r.created_at)}</td>
        <td>${escapeHtml(r.key_name || "")}</td>
        <td><code>${escapeHtml(r.endpoint || "")}</code></td>
        <td>${fmtNum(r.original_tokens)}</td>
        <td>${fmtNum(r.kept_tokens)}</td>
        <td>${Number(r.kv_savings_pct || 0).toFixed(1)}%</td>
      </tr>`
        )
        .join("")}</tbody></table>`;
  } catch (e) {
    if (e.message.includes("401") || e.message.includes("Sign in")) logout();
  }
}

async function loadKeys() {
  const el = $("#keys-list");
  try {
    const data = await api("GET", "/v1/dashboard/keys");
    const keys = data.keys || [];
    if (!keys.length) {
      el.innerHTML = '<p class="dash-empty">No keys yet. Create one to start calling the API.</p>';
      return;
    }
    el.innerHTML = keys
      .map(
        (k) => `<article class="key-card">
        <div class="key-card-body">
          <h3 class="key-card-name">${escapeHtml(k.name)}</h3>
          <code class="key-card-prefix">${escapeHtml(k.key_prefix)}…</code>
          <p class="key-card-meta">Created ${fmtTime(k.created_at)} · Last used ${fmtTime(k.last_used_at)}</p>
        </div>
        <button type="button" class="btn btn-outline btn-sm revoke-btn" data-id="${k.id}">Revoke</button>
      </article>`
      )
      .join("");
    $$(".revoke-btn", el).forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Revoke this key? Apps using it will stop working.")) return;
        await api("DELETE", `/v1/dashboard/keys/${btn.dataset.id}`);
        loadKeys();
        loadOverview();
      });
    });
  } catch (_) {
    el.innerHTML = '<p class="dash-empty">Could not load keys.</p>';
  }
}

function updateQuickstart() {
  /* Docs nav links to api.html */
}

async function runPlayground() {
  if (pgRunning) return;
  const key = $("#pg-key")?.value?.trim();
  const query = $("#pg-query")?.value?.trim() || "";
  const out = $("#pg-result");
  if (!key) {
    out.innerHTML = '<p class="pg-placeholder">Enter your API key.</p>';
    return;
  }
  localStorage.setItem(API_KEY_KEY, key);
  setPgRunning(true);
  showPgRunning(out);
  const body = { query, context_blocks: buildContextBlocks() };
  try {
    const r = await fetch(apiPath("/v1/agent/turn"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key, "ngrok-skip-browser-warning": "1" },
      body: JSON.stringify(body),
    });
    const text = await r.text();
    let d = {};
    try { d = JSON.parse(text); } catch { throw new Error("API returned invalid JSON."); }
    if (!r.ok) throw new Error(d.detail || "Failed");
    stopPgRunning();
    const s = d.memory || {};
    const phases = (d.phases || [])
      .map((p) => `<li><code>${escapeHtml(p.phase)}</code> ${escapeHtml(p.detail)}</li>`)
      .join("");
    out.innerHTML = `<div class="result-grid">
      <div class="stat"><span class="stat-n">${s.original_tokens ?? "—"}</span><span class="stat-l">tokens in</span></div>
      <div class="stat"><span class="stat-n">${s.kept_tokens ?? "—"}</span><span class="stat-l">kept</span></div>
      <div class="stat accent"><span class="stat-n">${s.kv_savings_pct ?? "—"}%</span><span class="stat-l">KV saved</span></div>
    </div>
    <p class="result-meta"><strong>Phases</strong></p><ul class="phase-list">${phases}</ul>
    <p class="result-meta"><strong>Answer</strong></p>
    <div class="result-preview">${escapeHtml(d.answer || "")}</div>`;
    loadOverview();
  } catch (e) {
    stopPgRunning();
    out.innerHTML = `<p class="pg-error">${escapeHtml(e.message)}</p>`;
  } finally {
    setPgRunning(false);
  }
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function showKeyModal(create = true) {
  const modal = $("#key-modal");
  modal.classList.remove("hidden");
  $("#modal-title").textContent = create ? "Create API key" : "API key created";
  $("#key-form").classList.toggle("hidden", !create);
  $("#key-reveal").classList.add("hidden");
  if (create) $("#key-form").reset();
}

function hideKeyModal() {
  $("#key-modal").classList.add("hidden");
}

async function login(email, password) {
  if (useFirebase) {
    await ScFirebase.signInWithEmail(email, password);
    return;
  }
  const data = await fetchJson("POST", "/v1/auth/login", { email, password });
  localStorage.setItem(TOKEN_KEY, data.token);
  showDash(data.user);
}

async function signup(name, email, password) {
  if (useFirebase) {
    await ScFirebase.createUserWithEmail(email, password, name);
    return;
  }
  const data = await fetchJson("POST", "/v1/auth/signup", { name, email, password });
  localStorage.setItem(TOKEN_KEY, data.token);
  showDash(data.user);
}

async function logout() {
  localStorage.removeItem(TOKEN_KEY);
  lastSyncedUid = null;
  currentFirebaseUser = null;
  if (useFirebase && window.ScFirebase?.ready) {
    try {
      await ScFirebase.signOut();
    } catch (_) {
      /* ignore */
    }
  }
  showAuth();
}

let integrationPollTimer = null;

function stopIntegrationPoll() {
  if (integrationPollTimer) {
    clearInterval(integrationPollTimer);
    integrationPollTimer = null;
  }
}

function startIntegrationPoll() {
  stopIntegrationPoll();
  let ticks = 0;
  loadIntegrations();
  integrationPollTimer = setInterval(() => {
    loadIntegrations();
    ticks += 1;
    if (ticks >= 40) stopIntegrationPoll();
  }, 3000);
}

async function loadIntegrations() {
  const el = $("#integrations-list");
  try {
    const data = await api("GET", "/v1/dashboard/integrations");
    const linked = new Set(data.linked || []);
    const toolkits = (data.toolkits || ["gmail", "github", "linear", "slack", "googlecalendar"]).filter(
      (tk) => tk !== "notion"
    );
    el.innerHTML = toolkits.map((tk) => {
      const on = linked.has(tk);
      const label = toolkitLabel(tk);
      return `<article class="int-card${on ? " int-card--on" : ""}">
        <div class="int-card-head">
          <span class="int-card-icon int-card-icon--logo">${toolkitLogo(tk)}</span>
          <div class="int-card-meta">
            <h3 class="int-card-name">${escapeHtml(label)}</h3>
            <span class="int-status${on ? " int-status--on" : ""}">${on ? "Connected" : "Not connected"}</span>
          </div>
        </div>
        ${on ? '<span class="int-connected-badge">Active</span>' : `<button type="button" class="btn btn-pear btn-sm connect-btn" data-tk="${tk}">Connect</button>`}
      </article>`;
    }).join("");
    $$(".connect-btn", el).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const res = await api("POST", `/v1/dashboard/integrations/connect/${btn.dataset.tk}`);
        if (res.already_connected) {
          loadIntegrations();
          return;
        }
        if (res.redirect_url) {
          window.open(res.redirect_url, "_blank", "noopener,noreferrer");
          startIntegrationPoll();
        } else {
          loadIntegrations();
        }
      });
    });
  } catch (_) {
    el.innerHTML = '<p class="dash-empty">Sign in to manage Composio connections.</p>';
  }
}

function bindAuth() {
  $$(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".auth-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const isLogin = tab.dataset.tab === "login";
      $("#login-form").classList.toggle("hidden", !isLogin);
      $("#signup-form").classList.toggle("hidden", isLogin);
      $("#auth-error").classList.add("hidden");
    });
  });

  $("#login-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await login(fd.get("email"), fd.get("password"));
    } catch (err) {
      const el = $("#auth-error");
      el.textContent = err.message;
      el.classList.remove("hidden");
    }
  });

  $("#signup-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      await signup(fd.get("name"), fd.get("email"), fd.get("password"));
    } catch (err) {
      const el = $("#auth-error");
      el.textContent = err.message;
      el.classList.remove("hidden");
    }
  });

  $("#logout-btn")?.addEventListener("click", () => logout());
  $("#logout-btn-mobile")?.addEventListener("click", () => logout());

  $("#google-signin-btn")?.addEventListener("click", async () => {
    const el = $("#auth-error");
    const btn = $("#google-signin-btn");
    try {
      el.classList.add("hidden");
      if (btn) {
        btn.disabled = true;
        btn.setAttribute("aria-busy", "true");
      }
      await ScFirebase.signInWithGoogle();
      if (btn) {
        btn.disabled = false;
        btn.removeAttribute("aria-busy");
      }
    } catch (err) {
      if (btn) {
        btn.disabled = false;
        btn.removeAttribute("aria-busy");
      }
      el.textContent = friendlyAuthError(err);
      el.classList.remove("hidden");
    }
  });
}

function friendlyAuthError(err) {
  const code = err?.code || "";
  const msg = err?.message || "";
  if (code === "auth/popup-blocked") return "Popup was blocked. Try again or use email sign-in.";
  if (code === "auth/unauthorized-domain") {
    return "This domain is not authorized in Firebase. Add supercompress.vercel.app to authorized domains.";
  }
  if (msg.includes("401") || msg.includes("Invalid") || msg.includes("expired")) {
    return "Signed in, but the API rejected your session. Check that the API is online.";
  }
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    return "Could not reach the API. Try again in a moment.";
  }
  return msg || "Sign-in failed";
}

async function syncFirebaseSession(user) {
  if (!user?.getIdToken) return false;
  if (lastSyncedUid === user.uid && $("#dash-screen") && !$("#dash-screen").classList.contains("hidden")) {
    return true;
  }
  if (sessionSyncing) return sessionSyncing;

  sessionSyncing = (async () => {
    try {
      currentFirebaseUser = user;
      const t = await user.getIdToken();
      localStorage.setItem(TOKEN_KEY, t);
      let profile = profileFromFirebase(user);
      let apiOffline = false;
      try {
        const data = await api("GET", "/v1/dashboard/me");
        profile = resolveDashboardUser(data, user) || profile;
      } catch (err) {
        if (!isApiOfflineError(err)) throw err;
        apiOffline = true;
      }
      if (!profile?.id && !profile?.email) {
        throw new Error("Could not load your profile. Try signing in again.");
      }
      lastSyncedUid = user.uid;
      hideAuthError();
      setApiOfflineBanner(apiOffline);
      return showDash(profile);
    } catch (err) {
      lastSyncedUid = null;
      localStorage.removeItem(TOKEN_KEY);
      setApiOfflineBanner(false);
      showAuth();
      showAuthError(friendlyAuthError(err));
      return false;
    } finally {
      sessionSyncing = null;
    }
  })();

  return sessionSyncing;
}

function bindDash() {
  $$(".dash-nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      setView(btn.dataset.view);
      if (btn.dataset.view === "integrations") loadIntegrations();
    });
  });

  $("#create-key-btn")?.addEventListener("click", () => showKeyModal(true));

  $("#key-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (creatingKey) return;
    creatingKey = true;
    const submitBtn = $("#key-form button[type=submit]");
    if (submitBtn) submitBtn.disabled = true;
    const name = new FormData(e.target).get("name") || "Default";
    try {
      const data = await api("POST", "/v1/dashboard/keys", { name });
      localStorage.setItem(API_KEY_KEY, data.api_key);
      $("#key-full").textContent = data.api_key;
      $("#key-form").classList.add("hidden");
      $("#key-reveal").classList.remove("hidden");
      if ($("#pg-key")) $("#pg-key").value = data.api_key;
    } catch (err) {
      alert(err.message);
    } finally {
      creatingKey = false;
      if (submitBtn) submitBtn.disabled = false;
    }
  });

  $("#copy-key-btn")?.addEventListener("click", () => {
    navigator.clipboard.writeText($("#key-full").textContent);
  });

  $("#key-done-btn")?.addEventListener("click", () => {
    hideKeyModal();
    loadKeys();
    loadOverview();
  });

  $("#pg-run")?.addEventListener("click", runPlayground);

  $("#pg-task-add")?.addEventListener("click", () => addPgItem("tasks", "#pg-task-input"));
  $("#pg-reminder-add")?.addEventListener("click", () => addPgItem("reminders", "#pg-reminder-input"));
  $("#pg-task-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); addPgItem("tasks", "#pg-task-input"); }
  });
  $("#pg-reminder-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); addPgItem("reminders", "#pg-reminder-input"); }
  });

  $("#key-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "key-modal") hideKeyModal();
  });

  window.addEventListener("focus", () => {
    if (!$("#view-integrations")?.classList.contains("hidden")) loadIntegrations();
  });
}

function showFirebaseAuthUi() {
  $("#google-signin-btn")?.classList.remove("hidden");
  $("#auth-divider")?.classList.remove("hidden");
}

async function resolveFirebaseConfig() {
  const baked = window.SUPERCOMPRESS_FIREBASE;
  if (baked?.enabled && baked.apiKey && baked.projectId) {
    return { auth: "firebase", firebase: baked };
  }
  try {
    const cfg = await fetchJson("GET", "/v1/auth/config");
    if (cfg.auth === "firebase" && cfg.firebase?.enabled) return cfg;
  } catch (_) {
    /* API unreachable — rely on baked config */
  }
  return null;
}

async function initFirebaseAuth() {
  const cfg = await resolveFirebaseConfig();
  if (!cfg) return false;

  useFirebase = true;
  showFirebaseAuthUi();
  await ScFirebase.init(cfg.firebase);

  try {
    await ScFirebase.completeRedirectSignIn();
  } catch (err) {
    showAuthError(friendlyAuthError(err));
  }

  ScFirebase.onAuthStateChanged(async (user) => {
    currentFirebaseUser = user;
    if (!user) {
      lastSyncedUid = null;
      localStorage.removeItem(TOKEN_KEY);
      setApiOfflineBanner(false);
      showAuth();
      return;
    }
    await syncFirebaseSession(user);
  });
  return true;
}

async function init() {
  bindAuth();
  bindDash();

  try {
    if (await initFirebaseAuth()) return;
  } catch (e) {
    console.warn("Firebase auth unavailable, using legacy login:", e.message);
  }

  if (token()) {
    try {
      const data = await api("GET", "/v1/dashboard/me");
      setApiOfflineBanner(false);
      if (showDash(resolveDashboardUser(data))) return;
    } catch (err) {
      if (!isApiOfflineError(err)) await logout();
    }
  }
  showAuth();
}

init();
