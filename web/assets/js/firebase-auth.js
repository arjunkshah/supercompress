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

  async function signInWithGoogle() {
    const provider = new global.firebase.auth.GoogleAuthProvider();
    return auth().signInWithPopup(provider);
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
    signOut,
    getIdToken,
    onAuthStateChanged,
  };
})(window);
