/** Landing — Datafruit-style mock + scroll reveals */

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function initScrollReveal() {
  const sections = document.querySelectorAll(".reveal-section");
  if (reducedMotion) {
    sections.forEach((s) => s.classList.add("is-visible"));
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("is-visible");
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -32px 0px" }
  );
  sections.forEach((s) => io.observe(s));
}

function initMockStackCycle() {
  const items = [...document.querySelectorAll("#mock-stack li")];
  if (!items.length || reducedMotion) return;
  let idx = 0;
  setInterval(() => {
    items.forEach((li) => li.classList.remove("active"));
    items[idx]?.classList.add("active");
    idx = (idx + 1) % items.length;
  }, 1800);
}

document.querySelectorAll(".api-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const parent = tab.closest(".mock-code") || tab.closest(".api-panel");
    parent?.querySelectorAll(".api-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const req = document.getElementById("api-code-request");
    const res = document.getElementById("api-code-response");
    const showRes = tab.dataset.tab === "response";
    if (showRes) {
      req?.classList.add("hidden");
      res?.classList.remove("hidden");
    } else {
      res?.classList.add("hidden");
      req?.classList.remove("hidden");
    }
  });
});

function initMobileNav() {
  const btn = document.getElementById("df-menu-btn");
  const menu = document.getElementById("df-mobile-nav");
  if (!btn || !menu) return;
  btn.addEventListener("click", () => {
    const open = menu.classList.toggle("hidden");
    btn.setAttribute("aria-expanded", open ? "false" : "true");
  });
}

initMobileNav();
initScrollReveal();
initMockStackCycle();
