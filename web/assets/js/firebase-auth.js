/** Firebase Auth client (compat SDK, loaded on demand). */
(function (global) {
  let ready = false;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const s = document.createElement("script");
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("Failed to load Firebase SDK"));
      document.head.appendChild(s);
    });
  }

  async function ensureSdk() {
    await loadScript("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
    await loadScript("https://www.gstatic.com/firebasejs/10.14.1/firebase-auth-compat.js");
  }

  async function init(config) {
    if (!config?.apiKey || !config?.projectId) {
      throw new Error("Firebase is not configured on the server.");
    }
    await ensureSdk();
    if (!global.firebase.apps.length) {
      global.firebase.initializeApp(config);
    }
    ready = true;
    return global.firebase.auth();
  }

  function auth() {
    if (!ready) throw new Error("Firebase not initialized");
    return global.firebase.auth();
  }

  function googleProvider() {
    const provider = new global.firebase.auth.GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    return provider;
  }

  async function signInWithEmail(email, password) {
    return auth().signInWithEmailAndPassword(email, password);
  }

  async function createUserWithEmail(email, password, displayName) {
    const cred = await auth().createUserWithEmailAndPassword(email, password);
    if (displayName && cred.user) {
      await cred.user.updateProfile({ displayName });
    }
    return cred;
  }

  /** Popup first (reliable on dashboard); redirect fallback if blocked. */
  async function signInWithGoogle() {
    try {
      return await auth().signInWithPopup(googleProvider());
    } catch (err) {
      const code = err?.code || "";
      if (code === "auth/popup-blocked" || code === "auth/cancelled-popup-request") {
        await auth().signInWithRedirect(googleProvider());
        return null;
      }
      throw err;
    }
  }

  /** Call once on page load after init to finish a Google redirect sign-in. */
  async function completeRedirectSignIn() {
    if (!ready) return null;
    try {
      const result = await auth().getRedirectResult();
      return result?.user || null;
    } catch (err) {
      const code = err?.code || "";
      if (code === "auth/no-auth-event") return null;
      throw err;
    }
  }

  async function signOut() {
    if (!ready) return;
    await auth().signOut();
  }

  async function getIdToken(forceRefresh = false) {
    const user = ready ? auth().currentUser : null;
    if (!user) return null;
    return user.getIdToken(forceRefresh);
  }

  function onAuthStateChanged(cb) {
    return auth().onAuthStateChanged(cb);
  }

  global.ScFirebase = {
    get ready() {
      return ready;
    },
    init,
    signInWithEmail,
    createUserWithEmail,
    signInWithGoogle,
    completeRedirectSignIn,
    signOut,
    getIdToken,
    onAuthStateChanged,
  };
})(window);
