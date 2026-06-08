/** SuperCompress developer dashboard */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

const TOKEN_KEY = "sc_token";
const API_KEY_KEY = "sc_api_key";
let useFirebase = false;
let sessionSyncing = null;

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
  const opts = { method, headers: { "Content-Type": "application/json", ...headers } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(apiPath(path), opts);
  const text = await r.text();
  let data = null;
  if (text) {
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

function showAuth() {
  $("#auth-screen")?.classList.remove("hidden");
  $("#dash-screen")?.classList.add("hidden");
  $("#logout-btn")?.classList.add("hidden");
  $("#logout-btn-mobile")?.classList.add("hidden");
}

function showAuthError(message) {
  const el = $("#auth-error");
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
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
  $("#logout-btn")?.classList.remove("hidden");
  $("#logout-btn-mobile")?.classList.remove("hidden");
  $("#user-label").textContent = user.name || user.email || "Signed in";
  loadOverview();
  loadKeys();
  loadIntegrations();
  updateQuickstart();
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
      el.innerHTML = '<p class="dim">No requests yet. Create a key and call the API.</p>';
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
      el.innerHTML = '<p class="dim">No keys yet. Create one to start calling the API.</p>';
      return;
    }
    el.innerHTML = keys
      .map(
        (k) => `<div class="key-row">
        <div>
          <strong>${escapeHtml(k.name)}</strong>
          <span class="key-prefix">${escapeHtml(k.key_prefix)}</span>
          <span class="dim">Created ${fmtTime(k.created_at)} · Last used ${fmtTime(k.last_used_at)}</span>
        </div>
        <button type="button" class="btn btn-ghost btn-sm revoke-btn" data-id="${k.id}">Revoke</button>
      </div>`
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
    el.innerHTML = '<p class="dim">Could not load keys.</p>';
  }
}

function updateQuickstart() {
  const key = localStorage.getItem(API_KEY_KEY) || "sc_live_YOUR_KEY";
  const base = (window.SUPERCOMPRESS_API || "https://supercompress-api.onrender.com").replace(/\/$/, "");
  $("#qs-curl").textContent = `curl -X POST ${base}/v1/agent/turn \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: ${key}" \\
  -d '{
    "query": "What should I focus on today?",
    "context_blocks": [
      "## User tasks\\n- Ship onboarding\\n- Fix reminder bug",
      "## Reminders\\n- Dentist Tue 3pm"
    ]
  }'`;
  $("#qs-python").textContent = `import httpx

r = httpx.post(
    "${base}/v1/agent/turn",
    headers={"X-API-Key": "${key}"},
    json={
        "query": user_message,
        "context_blocks": [
            f"## Tasks\\n{format_tasks(tasks)}",
            f"## Reminders\\n{format_reminders(reminders)}",
        ],
    },
    timeout=120,
)
data = r.json()
# Tavily + Composio + SuperCompress + Nebius — every call
print(data["answer"])  # show in your chat UI`;
  $("#qs-js").textContent = `const res = await fetch("${base}/v1/agent/turn", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": "${key}" },
  body: JSON.stringify({
    query: userMessage,
    context_blocks: [tasksBlock, remindersBlock],
  }),
});
const { answer, memory, stack } = await res.json();
// stack: { tavily, composio, supercompress, nebius } — all true`;
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
  if (useFirebase && window.ScFirebase?.ready) {
    try {
      await ScFirebase.signOut();
    } catch (_) {
      /* ignore */
    }
  }
  showAuth();
}

async function loadIntegrations() {
  const el = $("#integrations-list");
  try {
    const data = await api("GET", "/v1/dashboard/integrations");
    const linked = new Set(data.linked || []);
    el.innerHTML = (data.toolkits || ["gmail", "github", "linear"]).map((tk) => {
      const on = linked.has(tk);
      return `<div class="key-row">
        <div><strong>${tk}</strong><span class="dim">${on ? "Connected" : "Not connected"}</span></div>
        ${on ? "" : `<button type="button" class="btn btn-ghost btn-sm connect-btn" data-tk="${tk}">Connect</button>`}
      </div>`;
    }).join("");
    $$(".connect-btn", el).forEach((btn) => {
      btn.addEventListener("click", async () => {
        const res = await api("POST", `/v1/dashboard/integrations/connect/${btn.dataset.tk}`);
        if (res.redirect_url) window.open(res.redirect_url, "_blank");
        else loadIntegrations();
      });
    });
  } catch (_) {
    el.innerHTML = '<p class="dim">Sign in to manage Composio connections.</p>';
  }
}

async function runPlayground() {
  const key = $("#pg-key")?.value?.trim();
  const query = $("#pg-query")?.value || "";
  const contextRaw = $("#pg-context")?.value || "";
  const out = $("#pg-result");
  if (!key) {
    out.textContent = "Enter your API key.";
    return;
  }
  localStorage.setItem(API_KEY_KEY, key);
  updateQuickstart();
  out.innerHTML = '<p class="dim">Tavily → Composio → your blocks → compress → Nebius… (30–60s)</p>';
  const context_blocks = contextRaw.split("---").map((s) => s.trim()).filter(Boolean);
  const body = context_blocks.length > 1
    ? { query, context_blocks }
    : { query, context_blocks: contextRaw.trim() ? [contextRaw.trim()] : [] };
  try {
    const r = await fetch(apiPath("/v1/agent/turn"), {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": key },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || "Failed");
    const s = d.memory;
    const phases = (d.phases || [])
      .map((p) => `<li><code>${escapeHtml(p.phase)}</code> ${escapeHtml(p.detail)}</li>`)
      .join("");
    out.innerHTML = `<div class="result-grid">
      <div class="stat"><span class="stat-n">${s.original_tokens}</span><span class="stat-l">tokens in</span></div>
      <div class="stat"><span class="stat-n">${s.kept_tokens}</span><span class="stat-l">kept</span></div>
      <div class="stat accent"><span class="stat-n">${s.kv_savings_pct}%</span><span class="stat-l">KV saved</span></div>
    </div>
    <p class="result-meta"><strong>Phases</strong></p><ul class="phase-list">${phases}</ul>
    <p class="result-meta"><strong>Answer</strong></p>
    <pre class="result-preview">${escapeHtml(d.answer || "")}</pre>`;
    loadOverview();
  } catch (e) {
    out.textContent = e.message;
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
  if (sessionSyncing) return sessionSyncing;

  sessionSyncing = (async () => {
    const el = $("#auth-error");
    try {
      const t = await user.getIdToken();
      localStorage.setItem(TOKEN_KEY, t);
      const data = await api("GET", "/v1/dashboard/me");
      const profile = resolveDashboardUser(data, user);
      if (!profile) throw new Error("API did not return a user profile.");
      el?.classList.add("hidden");
      return showDash(profile);
    } catch (err) {
      localStorage.removeItem(TOKEN_KEY);
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
    const name = new FormData(e.target).get("name") || "Default";
    try {
      const data = await api("POST", "/v1/dashboard/keys", { name });
      localStorage.setItem(API_KEY_KEY, data.api_key);
      $("#key-full").textContent = data.api_key;
      $("#key-form").classList.add("hidden");
      $("#key-reveal").classList.remove("hidden");
      updateQuickstart();
      if ($("#pg-key")) $("#pg-key").value = data.api_key;
    } catch (err) {
      alert(err.message);
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

  $("#key-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "key-modal") hideKeyModal();
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
    // Consume Google redirect result; onAuthStateChanged performs the session sync.
    await ScFirebase.completeRedirectSignIn();
  } catch (err) {
    showAuthError(friendlyAuthError(err));
  }

  ScFirebase.onAuthStateChanged(async (user) => {
    if (!user) {
      localStorage.removeItem(TOKEN_KEY);
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
      if (showDash(resolveDashboardUser(data))) return;
    } catch (_) {
      await logout();
    }
  }
  showAuth();
}

init();
