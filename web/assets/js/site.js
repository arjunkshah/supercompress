/** Landing — hero grid, reveals, stack cycle, tabs */

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Exa-style hero grid
function buildHeroGrid() {
  const grid = document.getElementById("hero-grid");
  if (!grid || reducedMotion) return;
  const count = 84;
  for (let i = 0; i < count; i++) {
    const cell = document.createElement("div");
    cell.className = "hero-cell";
    cell.style.setProperty("--i", String(i % 20));
    grid.appendChild(cell);
    setTimeout(() => cell.classList.add("visible"), 30 + (i % 20) * 25);
  }
}

// Stagger hero reveals on load
function initHeroReveals() {
  document.querySelectorAll(".reveal, .reveal-scale").forEach((el) => {
    const d = el.dataset.delay || "0";
    el.style.setProperty("--delay", d);
    if (reducedMotion) {
      el.classList.add("is-visible");
      return;
    }
    requestAnimationFrame(() => {
      setTimeout(() => el.classList.add("is-visible"), 80 + Number(d) * 100);
    });
  });
}

// Scroll reveal sections
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
    { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
  );
  sections.forEach((s) => io.observe(s));
}

// Animate stack pipeline steps
function initStackCycle() {
  const wrap = document.getElementById("hero-stack");
  if (!wrap || reducedMotion) return;
  const steps = [...wrap.querySelectorAll(".stack-step")];
  let idx = 0;
  setInterval(() => {
    steps.forEach((s) => s.classList.remove("active"));
    steps[idx]?.classList.add("active");
    idx = (idx + 1) % steps.length;
  }, 1400);
}

// API request/response tabs with fade
document.querySelectorAll(".api-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".api-tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const req = document.getElementById("api-code-request");
    const res = document.getElementById("api-code-response");
    const showRes = tab.dataset.tab === "response";
    [req, res].forEach((el) => {
      if (!el) return;
      el.style.opacity = "0";
      el.style.transform = "translateY(6px)";
    });
    setTimeout(() => {
      if (showRes) {
        req?.classList.add("hidden");
        res?.classList.remove("hidden");
        res && animateCodeIn(res);
      } else {
        res?.classList.add("hidden");
        req?.classList.remove("hidden");
        req && animateCodeIn(req);
      }
    }, 150);
  });
});

function animateCodeIn(el) {
  el.style.transition = "opacity 0.35s ease, transform 0.35s ease";
  requestAnimationFrame(() => {
    el.style.opacity = "1";
    el.style.transform = "translateY(0)";
  });
}

// Feature tabs (Opennote)
document.querySelectorAll(".feature-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const id = tab.dataset.f;
    document.querySelectorAll(".feature-tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".feature-pane").forEach((p) => {
      p.classList.remove("active");
      p.style.opacity = "0";
    });
    tab.classList.add("active");
    const pane = document.querySelector(`.feature-pane[data-pane="${id}"]`);
    if (pane) {
      pane.classList.add("active");
      pane.style.opacity = "0";
      pane.style.transform = "translateY(8px)";
      requestAnimationFrame(() => {
        pane.style.transition = "opacity 0.4s ease, transform 0.4s ease";
        pane.style.opacity = "1";
        pane.style.transform = "translateY(0)";
      });
    }
  });
});

// Nav scroll shadow
const nav = document.querySelector(".nav");
window.addEventListener(
  "scroll",
  () => {
    if (!nav) return;
    nav.style.boxShadow = window.scrollY > 8 ? "0 4px 24px rgba(0,0,0,0.06)" : "none";
  },
  { passive: true }
);

buildHeroGrid();
initHeroReveals();
initScrollReveal();
initStackCycle();
