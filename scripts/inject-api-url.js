#!/usr/bin/env node
/** Bake API URL into static site at Vercel build time. */
const fs = require("fs");
const path = require("path");

// Empty = same-origin; Vercel rewrites /v1/* → Render (no CORS issues).
const apiUrl = process.env.SUPERCOMPRESS_API_URL || "";

const out = path.join(__dirname, "..", "web", "assets", "js", "config.js");
fs.writeFileSync(
  out,
  `// Auto-generated at Vercel build — "" uses /v1 proxy on same domain\nwindow.SUPERCOMPRESS_API = "${apiUrl.replace(/"/g, "")}";\n`
);
console.log("API URL:", apiUrl || "(same-origin /v1 proxy)");
