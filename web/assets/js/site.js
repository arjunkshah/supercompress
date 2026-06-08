/** Landing interactions — Exa tabs + Opennote feature tabs */

document.querySelectorAll(".api-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".api-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const req = document.getElementById("api-code-request");
    const res = document.getElementById("api-code-response");
    if (tab.dataset.tab === "response") {
      req?.classList.add("hidden");
      res?.classList.remove("hidden");
    } else {
      res?.classList.add("hidden");
      req?.classList.remove("hidden");
    }
  });
});

document.querySelectorAll(".feature-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const id = tab.dataset.f;
    document.querySelectorAll(".feature-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".feature-pane").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`.feature-pane[data-pane="${id}"]`)?.classList.add("active");
  });
});
