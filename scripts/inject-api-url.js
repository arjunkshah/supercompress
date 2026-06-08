#!/usr/bin/env node
/** Bake API URL into static site at Vercel build time. */
const fs = require("fs");
const path = require("path");

const apiUrl =
  process.env.SUPERCOMPRESS_API_URL ||
  process.env.RENDER_EXTERNAL_URL ||
  "https://supercompress-api.onrender.com";

const out = path.join(__dirname, "..", "web", "assets", "js", "config.js");
fs.writeFileSync(
  out,
  `// Auto-generated at build — official SuperCompress API\nwindow.SUPERCOMPRESS_API = "${apiUrl.replace(/"/g, "")}";\n`
);
console.log("API URL:", apiUrl);
