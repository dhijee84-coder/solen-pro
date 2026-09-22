/* Shared helpers used across every SuryaSetu page. */

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    credentials: "same-origin",
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const msg = (data && data.detail) ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

async function apiUpload(path, formData) {
  const res = await fetch(path, { method: "POST", body: formData, credentials: "same-origin" });
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (!res.ok) throw new Error((data && data.detail) || "Upload failed");
  return data;
}

async function downloadCsv(path, filename) {
  const res = await fetch(path, { credentials: "same-origin" });
  if (!res.ok) {
    let msg = "Export failed";
    try { const d = await res.json(); msg = d.detail || msg; } catch (e) {}
    throw new Error(msg);
  }
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename || "export.csv";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

const inr = (n) => "₹" + Math.round(n || 0).toLocaleString("en-IN");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const ico = (n, sz = 16) => `<svg class="ico" style="width:${sz}px;height:${sz}px" viewBox="0 0 24 24"><use href="#i-${n}"/></svg>`;
const fDate = (iso) => iso ? new Date(iso).toLocaleDateString("en-IN", {day:"2-digit", month:"short", year:"numeric"}) : "—";
const fDateTime = (iso) => iso ? new Date(iso).toLocaleString("en-IN", {day:"2-digit", month:"short", hour:"2-digit", minute:"2-digit", hour12:true}) : "—";

function toast(msg, isError) {
  let box = document.getElementById("toast-box");
  if (!box) {
    box = document.createElement("div");
    box.id = "toast-box";
    box.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:999;display:flex;flex-direction:column;gap:8px";
    document.body.appendChild(box);
  }
  const t = document.createElement("div");
  t.className = "card pad rise";
  t.style.cssText = `max-width:320px;font-size:13.5px;border-color:${isError ? "var(--alert)" : "var(--export)"}`;
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => t.remove(), 4200);
}

async function logout() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (e) {}
  window.location.href = "/login";
}

function emptyState(title, body) {
  return `<div class="empty-state"><div class="disp" style="font-weight:600;margin-bottom:6px">${esc(title)}</div><p style="color:var(--mute);margin:0">${esc(body)}</p></div>`;
}
function loadingState(label) {
  return `<div class="empty-state"><span class="spin">${ico("refresh",18)}</span><p style="color:var(--mute);margin:10px 0 0">${esc(label || "Loading…")}</p></div>`;
}
function errorState(msg) {
  return `<div class="empty-state" style="border-color:var(--alert)"><p style="color:var(--alert);margin:0">${esc(msg)}</p></div>`;
}

const THEME_KEY = "solan-theme";
function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}
function applyTheme(theme) {
  const t = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem(THEME_KEY, t); } catch (e) {}
  document.querySelectorAll(".theme-toggle").forEach((btn) => {
    btn.setAttribute("aria-pressed", t === "light" ? "true" : "false");
    btn.title = t === "light" ? "Switch to night mode" : "Switch to day mode";
  });
}
function toggleTheme() {
  applyTheme(currentTheme() === "dark" ? "light" : "dark");
}
(function bootTheme() {
  let stored = null;
  try { stored = localStorage.getItem(THEME_KEY); } catch (e) {}
  if (stored === "light" || stored === "dark") applyTheme(stored);
  else if (!document.documentElement.getAttribute("data-theme")) {
    const prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    applyTheme(prefersLight ? "light" : "dark");
  } else {
    applyTheme(currentTheme());
  }
})();

function warrantyPill(status) {
  const s = (status || "").toUpperCase();
  const map = {
    ACTIVE: "p-done",
    EXPIRING_SOON: "p-due",
    EXPIRED: "p-alert",
    VOID: "p-lock",
    CLAIM_IN_PROGRESS: "p-live",
    CLAIM_APPROVED: "p-done",
    CLAIM_REJECTED: "p-alert",
  };
  return `<span class="pill ${map[s] || "p-live"}">${esc(s.replace(/_/g, " "))}</span>`;
}

function claimPill(status) {
  const s = (status || "").toUpperCase();
  const map = {
    SUBMITTED: "p-live", UNDER_REVIEW: "p-live", MORE_INFORMATION_REQUIRED: "p-due",
    APPROVED: "p-done", REJECTED: "p-alert", REPLACEMENT_REQUIRED: "p-due",
    REPLACED: "p-done", REPAIRED: "p-done", CLOSED: "p-lock",
  };
  return `<span class="pill ${map[s] || "p-live"}">${esc(s.replace(/_/g, " "))}</span>`;
}
