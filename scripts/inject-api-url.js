#!/usr/bin/env node
/** Bake API URL + Firebase web config into static site at Vercel build time. */
const fs = require("fs");
const path = require("path");

const apiUrl = process.env.SUPERCOMPRESS_API_URL || "";

const firebase = {
  apiKey: process.env.FIREBASE_API_KEY || "",
  authDomain: process.env.FIREBASE_AUTH_DOMAIN || "",
  projectId: process.env.FIREBASE_PROJECT_ID || "",
  appId: process.env.FIREBASE_APP_ID || "",
  messagingSenderId: process.env.FIREBASE_MESSAGING_SENDER_ID || "",
};
const firebaseEnabled = Boolean(firebase.apiKey && firebase.projectId);
if (!firebase.authDomain && firebase.projectId) {
  firebase.authDomain = `${firebase.projectId}.firebaseapp.com`;
}

const out = path.join(__dirname, "..", "web", "assets", "js", "config.js");
const lines = [
  "// Auto-generated at build — do not edit",
  `window.SUPERCOMPRESS_API = "${apiUrl.replace(/"/g, "")}";`,
  "window.SUPERCOMPRESS_FIREBASE = " + JSON.stringify({ enabled: firebaseEnabled, ...firebase }, null, 2) + ";",
];
fs.writeFileSync(out, lines.join("\n") + "\n");

console.log("API URL:", apiUrl || "(same-origin /v1 proxy)");
console.log("Firebase:", firebaseEnabled ? "enabled" : "disabled");
