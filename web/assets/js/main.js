const lines = [
  { t: 0, s: "$ ./bin/supercompress turns", c: "dim" },
  { t: 400, s: "", c: "" },
  { t: 500, s: "Turn 1 · 2 blocks · ~24 words raw", c: "dim" },
  { t: 700, s: "  FIFO:           57 tokens kept", c: "" },
  { t: 900, s: "  SuperCompress:  57 tokens  (65% KV saved)", c: "ok" },
  { t: 1200, s: "", c: "" },
  { t: 1300, s: "Turn 2 · 4 blocks · ~48 words raw", c: "dim" },
  { t: 1500, s: "  FIFO:           57 tokens kept", c: "" },
  { t: 1700, s: "  SuperCompress:  57 tokens  (65% KV saved)", c: "ok" },
  { t: 2000, s: "", c: "" },
  { t: 2100, s: "Turn 3 · 6 blocks · growing…", c: "warn" },
  { t: 2300, s: "  SuperCompress:  still ~65% saved", c: "ok" },
  { t: 2600, s: "", c: "" },
  { t: 2700, s: "Turn 4 · 9 blocks · without us → OOM", c: "warn" },
  { t: 2900, s: "  SuperCompress:  agent keeps going ✓", c: "ok" },
  { t: 3200, s: "", c: "" },
  { t: 3400, s: "$ ./bin/supercompress loop", c: "dim" },
  { t: 3800, s: "Tavily → Composio → compress → Nebius → act", c: "ok" },
];

const el = document.getElementById("terminal");
if (el) {
  const rendered = new Set();
  const tick = () => {
    const now = Date.now() - start;
    lines.forEach((line, i) => {
      if (line.t <= now && !rendered.has(i)) {
        rendered.add(i);
        const span = document.createElement("span");
        if (line.c) span.className = line.c;
        span.textContent = line.s + (line.s ? "\n" : "");
        el.appendChild(span);
        el.scrollTop = el.scrollHeight;
      }
    });
    if (rendered.size < lines.length) requestAnimationFrame(tick);
  };
  const start = Date.now();
  tick();
  setInterval(() => {
    el.innerHTML = "";
    rendered.clear();
    const restart = Date.now();
    const loop = () => {
      const now = Date.now() - restart;
      lines.forEach((line, i) => {
        if (line.t <= now && !rendered.has(i)) {
          rendered.add(i);
          const span = document.createElement("span");
          if (line.c) span.className = line.c;
          span.textContent = line.s + (line.s ? "\n" : "");
          el.appendChild(span);
        }
      });
      if (rendered.size < lines.length) requestAnimationFrame(loop);
    };
    loop();
  }, 12000);
}
