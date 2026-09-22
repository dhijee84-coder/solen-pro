const ROLE = document.getElementById("shell").dataset.role;
let CTAB = "dashboard";
let ME = null;

const NAV = {
  ADMIN: [
    ["dashboard", "Dashboard", "trend"],
    ["clients", "Clients", "users"],
    ["projects", "Projects & panels", "panel"],
    ["allocate", "Allocate panels", "zap"],
    ["warranty", "Warranty claims", "shield"],
    ["payments", "Payments", "wallet"],
    ["services", "Services", "settings"],
    ["tickets", "Support tickets", "bell"],
    ["documents", "Documents", "file"],
    ["enquiries", "Enquiries", "file"],
    ["notifications", "Notifications", "bell"],
  ],
  SUPER_ADMIN: [
    ["dashboard", "Dashboard", "trend"],
    ["clients", "Clients", "users"],
    ["projects", "Projects & panels", "panel"],
    ["allocate", "Allocate panels", "zap"],
    ["warranty", "Warranty claims", "shield"],
    ["payments", "Payments", "wallet"],
    ["services", "Services", "settings"],
    ["tickets", "Support tickets", "bell"],
    ["documents", "Documents", "file"],
    ["enquiries", "Enquiries", "file"],
    ["staff", "Admins", "shield"],
    ["reports", "Reports", "activity"],
    ["audit", "Audit logs", "lock"],
    ["notifications", "Notifications", "bell"],
  ],
  PRIMARY_ADMIN: [
    ["dashboard", "Organization", "trend"],
    ["staff", "Admins & Super Admins", "shield"],
    ["clients", "Clients", "users"],
    ["projects", "Projects & panels", "panel"],
    ["allocate", "Allocate panels", "zap"],
    ["warranty", "Warranty claims", "shield"],
    ["payments", "Payments", "wallet"],
    ["services", "Services", "settings"],
    ["tickets", "Support tickets", "bell"],
    ["enquiries", "Enquiries", "file"],
    ["website", "Website CMS", "file"],
    ["faqs", "FAQs", "file"],
    ["announcements", "Announcements", "bell"],
    ["permissions", "Roles & permissions", "lock"],
    ["settings", "System settings", "settings"],
    ["reports", "Reports", "activity"],
    ["audit", "Audit logs", "lock"],
    ["notifications", "Notifications", "bell"],
  ],
};

async function boot() {
  try { ME = await api("/api/auth/me"); } catch (e) { window.location.href = "/staff-login"; return; }
  document.getElementById("hdr-name").textContent = `${ME.name} (${ME.role.replace("_"," ")})`;
  document.getElementById("rail-nav").innerHTML = NAV[ROLE].map(([id, label, icon]) => `
    <button class="rail-btn ${CTAB === id ? "on" : ""}" onclick="gotoTab('${id}')">${ico(icon,15)}<span style="flex:1">${label}</span></button>`).join("");
  gotoTab("dashboard");
}

function gotoTab(id) {
  CTAB = id;
  document.querySelectorAll("#rail-nav .rail-btn").forEach((b,i) => b.className = "rail-btn" + (NAV[ROLE][i][0]===id ? " on" : ""));
  const fns = {
    dashboard: ROLE === "PRIMARY_ADMIN" ? loadPrimaryDashboard : loadDashboard,
    clients: loadClients, projects: loadProjects, allocate: loadAllocate,
    payments: loadPayments, services: loadServices, tickets: loadTickets,
    documents: loadDocuments, staff: loadStaff, reports: loadReports,
    audit: loadAudit, notifications: loadNotifications,
    warranty: loadWarrantyClaims, enquiries: loadEnquiries,
    website: loadWebsiteCms, faqs: loadFaqs, announcements: loadAnnouncements,
    permissions: loadPermissions, settings: loadSettings,
  };
  (fns[id] || loadDashboard)();
  window.scrollTo(0,0);
}

function kpi(label, value, color) {
  return `<div class="kpi"><div class="eyebrow">${esc(label)}</div><div class="kpi-v" style="${color?`color:${color}`:""}">${value}</div></div>`;
}

/* ── dashboard ── */
async function loadDashboard() {
  const d = await api("/api/admin/dashboard");
  const c = d.cards;
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Operations dashboard</h2>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
      ${kpi("Total clients", c.total_clients)} ${kpi("New today", c.new_clients_today, "var(--sky)")}
      ${kpi("Active projects", c.active_projects)} ${kpi("Near capacity", c.projects_near_capacity, "var(--flux)")}
      ${kpi("Full", c.projects_full, "var(--alert)")} ${kpi("Panels available", c.panels_available)}
      ${kpi("Panels allocated", c.panels_allocated)} ${kpi("Pending payments", c.pending_payments)}
      ${kpi("Today's payments", c.todays_payments, "var(--export)")} ${kpi("Open tickets", c.open_tickets)}
      ${kpi("Pending documents", c.pending_documents)} ${kpi("Pending services", c.pending_service_requests)}
      ${kpi("Expiring warranties", c.expiring_warranties || 0, "var(--flux)")} ${kpi("Open claims", c.open_warranty_claims || 0)}
      ${kpi("New enquiries", c.new_enquiries || 0, "var(--sky)")}
    </div>
    <div class="card pad" style="margin-top:22px">
      <div class="disp" style="font-weight:600;margin-bottom:10px">Recent activity</div>
      <div class="wrap"><table class="tbl"><thead><tr><th>Action</th><th>Entity</th><th>When</th></tr></thead>
        <tbody>${d.recent_activity.map(a => `<tr><td>${esc(a.action)}</td><td class="mono">${esc(a.entity_type)} ${esc(a.entity_id)}</td><td>${fDateTime(a.timestamp)}</td></tr>`).join("") || '<tr><td colspan="3" style="color:var(--mute)">Nothing yet.</td></tr>'}</tbody>
      </table></div>
    </div>`;
}

async function loadPrimaryDashboard() {
  const d = await api("/api/primary-admin/dashboard");
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Organizational control</h2>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
      ${kpi("Super Admins", d.total_super_admins)} ${kpi("Active Super Admins", d.active_super_admins, "var(--export)")}
      ${kpi("Admins", d.total_admins)} ${kpi("Active Admins", d.active_admins, "var(--export)")}
      ${kpi("Inactive Admins", d.inactive_admins, "var(--alert)")}
    </div>
    <div class="card pad" style="margin-top:20px">
      <div class="disp" style="font-weight:600;margin-bottom:10px">Platform totals</div>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr))">
        ${kpi("Users", d.totals.users)} ${kpi("Clients", d.totals.clients)} ${kpi("Projects", d.totals.projects)}
        ${kpi("Panels", d.totals.panels)} ${kpi("Payments", d.totals.payments)}
      </div>
    </div>
    <div class="card pad" style="margin-top:20px">
      <div class="disp" style="font-weight:600;margin-bottom:10px">Recent administrative actions</div>
      <div class="wrap"><table class="tbl"><thead><tr><th>Action</th><th>Entity</th><th>Detail</th><th>When</th></tr></thead>
        <tbody>${d.recent_role_changes.map(a => `<tr><td>${esc(a.action)}</td><td class="mono">${esc(a.entity_id)}</td><td>${esc(a.new_value)}</td><td>${fDateTime(a.timestamp)}</td></tr>`).join("") || '<tr><td colspan="4" style="color:var(--mute)">No changes yet.</td></tr>'}</tbody>
      </table></div>
    </div>`;
}

/* ── clients ── */
async function loadClients() {
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Clients</h2>
    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;align-items:center">
      <input id="client-search" class="field" placeholder="Search by name, phone, email, client ID…" style="max-width:340px" oninput="debounceClientSearch()">
      ${canExport() ? `<button class="btn sm" onclick="doExport('/api/admin/export/clients','clients.csv')">Export CSV</button>` : ""}
    </div>
    <div id="client-table" class="card wrap"></div>`;
  renderClientTable(await api("/api/admin/clients"));
}
let _searchTimer;
function debounceClientSearch() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(async () => {
    const q = document.getElementById("client-search").value;
    renderClientTable(await api("/api/admin/clients?q=" + encodeURIComponent(q)));
  }, 300);
}
function renderClientTable(clients) {
  document.getElementById("client-table").innerHTML = `<table class="tbl">
    <thead><tr><th>Client</th><th>Phone</th><th>KYC</th><th>Project</th><th>Panels</th><th>Payment</th><th></th></tr></thead>
    <tbody>${clients.map(c => `<tr>
      <td>${esc(c.name)}<div class="mono" style="color:var(--mute);font-size:11px">${c.id}</div></td>
      <td class="mono">${esc(c.phone||"—")}</td>
      <td><span class="pill ${c.kyc_status==='VERIFIED'?'p-done':'p-due'}">${c.kyc_status}</span></td>
      <td>${esc(c.project||"—")}</td><td>${c.panels}</td>
      <td><span class="pill ${c.payment_status==='SUCCESS'?'p-done':'p-live'}">${c.payment_status}</span></td>
      <td><button class="btn sm" onclick="openClientDetail('${c.id}')">View</button></td>
    </tr>`).join("") || `<tr><td colspan="7" style="color:var(--mute);padding:16px">No clients found.</td></tr>`}</tbody></table>`;
}

async function openClientDetail(id) {
  const d = await api("/api/admin/clients/" + id);
  const p = d.profile;
  document.getElementById("main").innerHTML = `
    <button class="btn sm bare" onclick="loadClients()">← Back to clients</button>
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:12px 0">${esc(p.name)} <span class="mono" style="font-size:13px;color:var(--mute)">${p.id}</span></h2>
    <div class="grid" style="grid-template-columns:2fr 1fr;gap:18px" id="detail-grid">
      <div>
        <div class="card pad">
          <div class="disp" style="font-weight:600;margin-bottom:10px">Profile</div>
          <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
            ${kv("Phone", p.phone)} ${kv("Email", p.email||"—")} ${kv("KYC", p.kyc_status)}
            ${kv("PAN", p.pan_number||"—")} ${kv("Aadhaar", p.aadhaar_masked||"—")} ${kv("Onboarding", p.onboarding_stage)}
          </div>
          <label class="lab" style="margin-top:14px">Admin notes</label>
          <textarea id="admin-notes" class="field" rows="2">${esc(p.admin_notes||"")}</textarea>
          <button class="btn sm" style="margin-top:8px" onclick="saveNotes('${p.id}')">Save notes</button>
        </div>
        ${d.project ? `<div class="card pad" style="margin-top:14px">
          <div class="disp" style="font-weight:600;margin-bottom:10px">Project &amp; panels</div>
          ${kv("Project", d.project.project_name)} ${kv("Panels", d.project.allocated_panels)} ${kv("Capacity", d.project.allocated_capacity_kw.toFixed(2)+" kW")}
        </div>` : ""}
        <div class="card pad" style="margin-top:14px">
          <div class="disp" style="font-weight:600;margin-bottom:10px">Project stages</div>
          <div class="wrap"><table class="tbl"><thead><tr><th>#</th><th>Stage</th><th>Status</th><th></th></tr></thead>
            <tbody>${d.stages.map(s => `<tr><td>${s.number}</td><td>${esc(s.name)}</td><td><span class="pill p-live">${s.status}</span></td>
              <td><select class="field" style="width:auto;padding:5px 8px" onchange="updateStage('${s.id}',this.value,'${p.id}')">
                ${["NOT_STARTED","IN_PROGRESS","PAYMENT_DUE","COMPLETED","BLOCKED"].map(o=>`<option ${o===s.status?"selected":""}>${o}</option>`).join("")}
              </select></td></tr>`).join("") || `<tr><td colspan="4" style="color:var(--mute)">No stages yet — allocate panels to create them.</td></tr>`}</tbody></table></div>
        </div>
        <div class="card pad" style="margin-top:14px">
          <div class="disp" style="font-weight:600;margin-bottom:10px">Documents</div>
          <div class="wrap"><table class="tbl"><thead><tr><th>Type</th><th>File</th><th>Status</th><th></th></tr></thead>
            <tbody>${d.documents.map(doc => `<tr><td>${doc.type}</td><td>${esc(doc.filename||"—")}</td><td><span class="pill ${doc.status==='VERIFIED'?'p-done':'p-due'}">${doc.status}</span></td>
              <td>
                <a class="btn sm" href="/api/admin/documents/${doc.id}/file" target="_blank" rel="noopener">Download</a>
                ${doc.status==='UPLOADED' ? `<button class="btn sm" onclick="verifyDoc('${p.id}','${doc.id}',true)">Approve</button> <button class="btn sm" onclick="verifyDoc('${p.id}','${doc.id}',false)">Reject</button>` : ""}
              </td></tr>`).join("") || `<tr><td colspan="4" style="color:var(--mute)">No documents.</td></tr>`}</tbody></table></div>
        </div>
      </div>
      <div>
        <div class="card pad">
          <div class="disp" style="font-weight:600;margin-bottom:10px">Record a payment</div>
          <label class="lab">Amount (₹)</label><input id="pay-amount" class="field" type="number" style="margin-bottom:10px">
          <button class="btn flux wide" onclick="recordPayment('${p.id}')">Record payment</button>
        </div>
        <div class="card pad" style="margin-top:14px">
          <div class="disp" style="font-weight:600;margin-bottom:10px">Payment history</div>
          ${d.payments.map(x => `<div style="display:flex;justify-content:space-between;font-size:12.5px;padding:6px 0;border-bottom:1px solid var(--edge)">
            <span>${fDate(x.created_at)} · ${esc(x.method)}</span><span class="mono">${inr(x.amount)}</span></div>`).join("") || `<span style="color:var(--mute);font-size:12.5px">None yet.</span>`}
        </div>
      </div>
    </div>`;
}
async function saveNotes(id) {
  await api(`/api/admin/clients/${id}`, { method: "PUT", body: { admin_notes: document.getElementById("admin-notes").value } });
  toast("Notes saved.");
}
async function updateStage(stageId, status, clientId) {
  await api(`/api/admin/stages/${stageId}`, { method: "PUT", body: { status } });
  toast("Stage updated.");
  openClientDetail(clientId);
}
async function verifyDoc(clientId, docId, approve) {
  await api(`/api/admin/clients/${clientId}/verify-document/${docId}?approve=${approve}`, { method: "POST" });
  toast(approve ? "Document verified." : "Document rejected.");
  openClientDetail(clientId);
}
async function recordPayment(clientId) {
  const amount = parseFloat(document.getElementById("pay-amount").value);
  if (!amount) return;
  await api(`/api/admin/clients/${clientId}/payments`, { method: "POST", body: { amount, method: "MANUAL" } });
  toast("Payment recorded.");
  openClientDetail(clientId);
}

/* ── projects & panels ── */
async function loadProjects() {
  const projects = await api("/api/admin/projects");
  const canCreateProject = ROLE === "PRIMARY_ADMIN" || ROLE === "SUPER_ADMIN";
  document.getElementById("main").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">Projects &amp; sites</h2>
      ${canCreateProject ? `<button class="btn flux sm" onclick="openNewProject()">+ New project</button>` : ""}
    </div>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr));margin-top:16px">
      ${projects.map(p => {
        const barClass = p.status === "FULL" ? "full" : p.utilization >= 90 ? "crit" : p.utilization >= 80 ? "warn" : "";
        return `<div class="card pad">
          <div style="display:flex;justify-content:space-between"><div class="disp" style="font-weight:600">${esc(p.name)}</div>
            <span class="pill ${p.status==='FULL'?'p-alert':p.status==='ACTIVE'?'p-done':'p-live'}">${p.status}</span></div>
          <div class="mono" style="color:var(--mute);font-size:12px;margin:4px 0 10px">${esc(p.code)} · ${esc(p.location||"—")}</div>
          <div class="bar-outer"><div class="bar-inner ${barClass}" style="width:${p.utilization}%"></div></div>
          <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-top:8px;color:var(--mute)">
            <span>${p.allocated_panels}/${p.total_panels} panels (${p.utilization}%)</span><span>${p.capacity_kw.toFixed(1)} kW</span>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px">
            ${(ROLE === "PRIMARY_ADMIN" || ROLE === "SUPER_ADMIN") ? `<button class="btn sm" onclick="openAddPanels('${p.id}')">+ Add panels</button>` : ""}
            <button class="btn sm" onclick="viewPanels('${p.id}')">View panels</button>
            ${(ROLE === "PRIMARY_ADMIN" || ROLE === "SUPER_ADMIN") ? `<button class="btn sm" onclick="togglePublic('${p.id}', ${p.is_public ? 'false' : 'true'})">${p.is_public ? "Unpublish" : "Make public"}</button>` : ""}
          </div>
        </div>`;
      }).join("") || '<span style="color:var(--mute)">No projects yet.</span>'}
    </div>
    <div id="panels-view" style="margin-top:20px"></div>`;
}
function openNewProject() {
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise"><div class="sheet-hd"><div class="disp" style="font-weight:600">New project</div><button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
    <div class="sheet-body">
      <label class="lab">Project code</label><input id="np-code" class="field" style="margin-bottom:10px" placeholder="CHN-002">
      <label class="lab">Project name</label><input id="np-name" class="field" style="margin-bottom:10px" placeholder="Chennai Solar Park B">
      <label class="lab">Location</label><input id="np-loc" class="field" style="margin-bottom:14px" placeholder="Chennai, TN">
      <button class="btn flux wide" onclick="createProject()">Create project</button>
    </div></div></div>`;
}
async function createProject() {
  const project_code = document.getElementById("np-code").value.trim();
  const project_name = document.getElementById("np-name").value.trim();
  const location = document.getElementById("np-loc").value.trim();
  if (!project_code || !project_name) return;
  await api("/api/admin/projects", { method: "POST", body: { project_code, project_name, location } });
  document.getElementById("modal").innerHTML = "";
  toast("Project created.");
  loadProjects();
}
function openAddPanels(projectId) {
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise"><div class="sheet-hd"><div class="disp" style="font-weight:600">Add panels</div><button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
    <div class="sheet-body">
      <label class="lab">Count</label><input id="ap-count" type="number" class="field" style="margin-bottom:10px" value="50">
      <label class="lab">Watt rating</label><input id="ap-watt" type="number" class="field" style="margin-bottom:14px" value="400">
      <button class="btn flux wide" onclick="addPanels('${projectId}')">Add panels</button>
    </div></div></div>`;
}
async function addPanels(projectId) {
  const count = parseInt(document.getElementById("ap-count").value, 10);
  const watt_rating = parseInt(document.getElementById("ap-watt").value, 10);
  const r = await api(`/api/admin/projects/${projectId}/panels`, { method: "POST", body: { project_id: projectId, count, watt_rating } });
  document.getElementById("modal").innerHTML = "";
  toast(`Added ${r.added} panels (${r.first_serial} → ${r.last_serial}).`);
  loadProjects();
}
async function viewPanels(projectId) {
  const panels = await api("/api/admin/panels?project_id=" + projectId);
  document.getElementById("panels-view").innerHTML = `
    <div class="card wrap"><table class="tbl"><thead><tr><th>Seq</th><th>Serial</th><th>Status</th><th>Client</th></tr></thead>
    <tbody>${panels.map(p => `<tr><td>${p.added_sequence}</td><td class="mono">${p.serial_number}</td>
      <td><span class="pill ${p.status==='AVAILABLE'?'p-done':p.status==='ALLOCATED'?'p-live':'p-due'}">${p.status}</span></td>
      <td>${p.client_id ? `<span class="mono">${p.client_id}</span> <button class="btn sm" onclick="deallocatePanel('${p.id}','${projectId}')">Release</button>` : "—"}</td></tr>`).join("")}</tbody></table></div>`;
}
async function deallocatePanel(panelId, projectId) {
  await api(`/api/admin/panels/${panelId}/deallocate`, { method: "POST" });
  toast("Panel released back to available pool.");
  viewPanels(projectId);
  loadProjects();
}

/* ── allocation ── */
async function loadAllocate() {
  const [projects, clients] = await Promise.all([api("/api/admin/projects"), api("/api/admin/clients")]);
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Allocate panels (FIFO)</h2>
    <div class="card pad" style="max-width:520px">
      <label class="lab">Project</label>
      <select id="al-project" class="field" style="margin-bottom:12px" onchange="previewAllocation()">
        ${projects.map(p => `<option value="${p.id}">${esc(p.name)} — ${p.available_panels} available</option>`).join("")}
      </select>
      <label class="lab">Client</label>
      <select id="al-client" class="field" style="margin-bottom:12px">
        ${clients.map(c => `<option value="${c.id}">${esc(c.name)} (${c.id})</option>`).join("")}
      </select>
      <label class="lab">Panel count</label>
      <input id="al-count" type="number" class="field" value="10" style="margin-bottom:12px" oninput="previewAllocation()">
      <div id="al-preview" style="font-size:12.5px;color:var(--mute);margin-bottom:14px"></div>
      <button class="btn flux wide" onclick="confirmAllocation()">Allocate &amp; provision project</button>
    </div>`;
  previewAllocation();
}
async function previewAllocation() {
  const project_id = document.getElementById("al-project").value;
  const count = parseInt(document.getElementById("al-count").value, 10) || 0;
  if (!project_id || !count) return;
  const r = await api(`/api/admin/allocate/preview?project_id=${project_id}&count=${count}`);
  document.getElementById("al-preview").innerHTML = r.sufficient
    ? `<span style="color:var(--export)">FIFO preview: ${r.serials.slice(0,6).join(", ")}${r.serials.length>6?" …":""}</span>`
    : `<span style="color:var(--alert)">Only ${r.available_shown} of ${count} panels available in this project.</span>`;
}
async function confirmAllocation() {
  const project_id = document.getElementById("al-project").value;
  const client_id = document.getElementById("al-client").value;
  const panel_count = parseInt(document.getElementById("al-count").value, 10);
  try {
    await api(`/api/admin/clients/${client_id}/assign-project?project_id=${project_id}&panel_count=${panel_count}`, { method: "POST" });
    toast("Panels allocated and project stages created.");
    loadAllocate();
  } catch (e) { toast(e.message, true); }
}

/* ── payments ── */
async function loadPayments() {
  const pays = await api("/api/admin/payments");
  document.getElementById("main").innerHTML = `
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">Payments</h2>
      ${canExport() ? `<button class="btn sm" onclick="doExport('/api/admin/export/payments','payments.csv')">Export CSV</button>` : ""}
    </div>
    <div class="card wrap" style="margin-top:16px"><table class="tbl"><thead><tr><th>Client</th><th>Amount</th><th>Method</th><th>Status</th><th>First?</th><th>When</th></tr></thead>
      <tbody>${pays.map(p => `<tr><td>${esc(p.client_name)}</td><td class="mono">${inr(p.amount)}</td><td>${esc(p.method)}</td>
        <td><span class="pill ${p.status==='SUCCESS'?'p-done':'p-due'}">${p.status}</span></td><td>${p.is_first_payment?"Yes":""}</td><td>${fDateTime(p.created_at)}</td></tr>`).join("") || '<tr><td colspan="6" style="color:var(--mute)">No payments yet.</td></tr>'}</tbody></table></div>`;
}

/* ── services ── */
async function loadServices() {
  const [services, requests] = await Promise.all([api("/api/admin/services"), api("/api/admin/service-requests")]);
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Extra services</h2>
    <div class="card pad">
      <div class="disp" style="font-weight:600;margin-bottom:10px">Catalog</div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;align-items:flex-end">
        <div><label class="lab">Name</label><input id="sv-name" class="field"></div>
        <div><label class="lab">Base price</label><input id="sv-price" type="number" class="field" style="width:120px"></div>
        <button class="btn" onclick="createService()">Add</button>
      </div>
      <div class="wrap"><table class="tbl"><thead><tr><th>Name</th><th>Price</th><th>Active</th></tr></thead>
        <tbody>${services.map(s => `<tr><td>${esc(s.name)}</td><td>${s.base_price?inr(s.base_price):"—"}</td><td>${s.is_active?"Yes":"No"}</td></tr>`).join("")}</tbody></table></div>
    </div>
    <div class="card pad" style="margin-top:16px">
      <div class="disp" style="font-weight:600;margin-bottom:10px">Client requests</div>
      <div class="wrap"><table class="tbl"><thead><tr><th>Client</th><th>Service</th><th>Status</th><th>Quote</th><th></th></tr></thead>
        <tbody>${requests.map(r => `<tr><td>${esc(r.client_name)}</td><td>${esc(r.service)}</td><td><span class="pill p-live">${r.status}</span></td>
          <td>${r.quoted_price?inr(r.quoted_price):"—"}</td>
          <td><select class="field" style="width:auto;padding:5px 8px" onchange="updateServiceRequest('${r.id}',this.value)">
            ${["REQUESTED","UNDER_REVIEW","QUOTED","APPROVED","PAYMENT_PENDING","IN_PROGRESS","COMPLETED","REJECTED","CANCELLED"].map(o=>`<option ${o===r.status?"selected":""}>${o}</option>`).join("")}
          </select></td></tr>`).join("") || '<tr><td colspan="5" style="color:var(--mute)">No requests yet.</td></tr>'}</tbody></table></div>
    </div>`;
}
async function createService() {
  const name = document.getElementById("sv-name").value.trim();
  const base_price = parseFloat(document.getElementById("sv-price").value) || 0;
  if (!name) return;
  await api("/api/admin/services", { method: "POST", body: { name, base_price } });
  toast("Service added.");
  loadServices();
}
async function updateServiceRequest(id, status) {
  await api(`/api/admin/service-requests/${id}`, { method: "PUT", body: { status } });
  toast("Request updated.");
  loadServices();
}

/* ── tickets ── */
async function loadTickets() {
  const ts = await api("/api/admin/tickets");
  window._tickets = ts;
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Support tickets</h2>
    <div class="card wrap"><table class="tbl"><thead><tr><th>Client</th><th>Subject</th><th>Priority</th><th>Status</th><th></th></tr></thead>
      <tbody>${ts.map(t => `<tr><td>${esc(t.client_name)}</td><td>${esc(t.subject)}</td><td>${t.priority}</td>
        <td>${claimPill(t.status)}</td>
        <td><button class="btn sm" onclick="openStaffTicket('${t.id}')">Open</button></td></tr>`).join("") || '<tr><td colspan="5" style="color:var(--mute)">No tickets yet.</td></tr>'}</tbody></table></div>`;
}
async function openStaffTicket(id) {
  const t = await api("/api/admin/tickets/" + id);
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:540px">
      <div class="sheet-hd"><div><div class="disp" style="font-weight:600">${esc(t.subject)}</div>
        <div style="font-size:12.5px;color:var(--mute);margin-top:4px">${esc(t.client_name)} · ${esc(t.category||"")}</div></div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <p style="color:var(--mute);font-size:13.5px">${esc(t.description || "")}</p>
        <label class="lab" style="margin-top:10px">Status</label>
        <select id="tk-st" class="field" onchange="updateTicket('${t.id}',this.value)">
          ${["OPEN","ASSIGNED","IN_PROGRESS","WAITING_FOR_CLIENT","RESOLVED","CLOSED"].map(o=>`<option ${o===t.status?"selected":""}>${o}</option>`).join("")}
        </select>
        <div style="margin:14px 0;display:flex;flex-direction:column;gap:8px">
          ${(t.messages||[]).map(m => `<div class="card pad" style="padding:10px 12px">
            <div style="font-size:11px;color:var(--mute)">${m.mine?"You":"Client"} · ${fDateTime(m.created_at)}</div>
            <div style="margin-top:4px">${esc(m.message)}</div>
          </div>`).join("") || '<span style="color:var(--mute);font-size:13px">No conversation yet.</span>'}
        </div>
        <textarea id="tk-reply" class="field" rows="2" placeholder="Internal reply to client…"></textarea>
        <button class="btn flux wide" style="margin-top:10px" onclick="replyStaffTicket('${t.id}')">Send</button>
      </div>
    </div></div>`;
}
async function replyStaffTicket(id) {
  const message = document.getElementById("tk-reply").value.trim();
  if (!message) return;
  await api(`/api/admin/tickets/${id}/messages`, { method: "POST", body: { message } });
  toast("Reply sent.");
  openStaffTicket(id);
}
async function updateTicket(id, status) {
  await api(`/api/admin/tickets/${id}`, { method: "PUT", body: { status } });
  toast("Ticket updated.");
  loadTickets();
}

/* ── documents ── */
async function loadDocuments() {
  const docs = await api("/api/admin/documents");
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Documents</h2>
    <div class="card wrap"><table class="tbl"><thead><tr><th>Client</th><th>Type</th><th>File</th><th>Status</th><th></th></tr></thead>
      <tbody>${docs.map(d => `<tr><td>${esc(d.client_name)}</td><td>${d.type}</td><td>${esc(d.filename||"—")}</td>
        <td><span class="pill ${d.status==='VERIFIED'?'p-done':'p-due'}">${d.status}</span></td>
        <td>
          <a class="btn sm" href="/api/admin/documents/${d.id}/file" target="_blank" rel="noopener">Download</a>
          ${d.status==='UPLOADED'?`<button class="btn sm" onclick="quickVerify('${d.client_id}','${d.id}',true)">Approve</button> <button class="btn sm" onclick="quickVerify('${d.client_id}','${d.id}',false)">Reject</button>`:""}
        </td></tr>`).join("") || '<tr><td colspan="5" style="color:var(--mute)">No documents yet.</td></tr>'}</tbody></table></div>`;
}
async function quickVerify(clientId, docId, approve) {
  await api(`/api/admin/clients/${clientId}/verify-document/${docId}?approve=${approve}`, { method: "POST" });
  toast(approve ? "Document verified." : "Document rejected.");
  loadDocuments();
}

/* ── staff (super admin / primary admin) ── */
async function loadStaff() {
  const staff = await api("/api/admin/staff");
  document.getElementById("main").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">Administrators</h2>
      <button class="btn flux sm" onclick="openNewStaff()">+ New admin</button>
    </div>
    <div class="card wrap" style="margin-top:16px"><table class="tbl"><thead><tr><th>Name</th><th>Username</th><th>Role</th><th>Status</th><th></th></tr></thead>
      <tbody>${staff.map(s => `<tr><td>${esc(s.name)}</td><td class="mono">${esc(s.username)}</td><td>${s.role.replace("_"," ")}</td>
        <td><span class="pill ${s.is_active?'p-done':'p-due'}">${s.is_active?"Active":"Inactive"}</span></td>
        <td>${s.is_active ? `<button class="btn sm" onclick="removeStaff('${s.id}')">Deactivate</button>` : ""}</td></tr>`).join("") || '<tr><td colspan="5" style="color:var(--mute)">No staff yet.</td></tr>'}</tbody></table></div>`;
}
function openNewStaff() {
  const canSuper = ROLE === "PRIMARY_ADMIN";
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise"><div class="sheet-hd"><div class="disp" style="font-weight:600">New staff account</div><button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
    <div class="sheet-body">
      <label class="lab">Full name</label><input id="ns-name" class="field" style="margin-bottom:10px">
      <label class="lab">Username</label><input id="ns-user" class="field" style="margin-bottom:10px">
      <label class="lab">Password</label><input id="ns-pass" type="password" class="field" style="margin-bottom:10px">
      <label class="lab">Role</label>
      <select id="ns-role" class="field" style="margin-bottom:14px">
        <option value="ADMIN">Admin</option>
        ${canSuper ? '<option value="SUPER_ADMIN">Super Admin</option>' : ''}
      </select>
      <button class="btn flux wide" onclick="createStaff()">Create account</button>
    </div></div></div>`;
}
async function createStaff() {
  const full_name = document.getElementById("ns-name").value.trim();
  const username = document.getElementById("ns-user").value.trim();
  const password = document.getElementById("ns-pass").value;
  const role = document.getElementById("ns-role").value;
  if (!full_name || !username || !password) return;
  try {
    await api("/api/admin/staff", { method: "POST", body: { full_name, username, password, role } });
    document.getElementById("modal").innerHTML = "";
    toast("Staff account created.");
    loadStaff();
  } catch (e) { toast(e.message, true); }
}
async function removeStaff(id) {
  await api(`/api/admin/staff/${id}`, { method: "DELETE" });
  toast("Staff account deactivated.");
  loadStaff();
}

/* ── reports ── */
function canExport() { return ROLE === "PRIMARY_ADMIN" || ROLE === "SUPER_ADMIN"; }
async function loadReports() {
  const r = await api("/api/admin/reports/summary");
  const exp = canExport();
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Reports</h2>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr))">
      ${kpi("Total revenue", inr(r.total_revenue), "var(--export)")} ${kpi("Payments recorded", r.total_payments)} ${kpi("Total clients", r.total_clients)}
    </div>
    <div class="card pad" style="margin-top:20px">
      <div class="disp" style="font-weight:600;margin-bottom:10px">Project utilization</div>
      ${r.project_utilization.map(p => `<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px"><span>${esc(p.project)}</span><span class="mono">${p.utilization_pct}%</span></div>
        <div class="bar-outer"><div class="bar-inner ${p.utilization_pct>=100?'full':p.utilization_pct>=90?'crit':p.utilization_pct>=80?'warn':''}" style="width:${p.utilization_pct}%"></div></div></div>`).join("") || '<span style="color:var(--mute)">No projects yet.</span>'}
    </div>
    ${exp ? `<div class="card pad" style="margin-top:20px">
      <div class="disp" style="font-weight:600;margin-bottom:12px">CSV export</div>
      <p style="color:var(--mute);font-size:13px;margin:0 0 12px">Server-generated files. Exports are written to the audit log.</p>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        <button class="btn sm" onclick="doExport('/api/admin/export/clients','clients.csv')">Clients</button>
        <button class="btn sm" onclick="doExport('/api/admin/export/payments','payments.csv')">Payments</button>
        <button class="btn sm" onclick="doExport('/api/admin/export/panels','panels.csv')">Panels / warranties</button>
        <button class="btn sm" onclick="doExport('/api/admin/export/warranty-claims','warranty_claims.csv')">Warranty claims</button>
        <button class="btn sm" onclick="doExport('/api/admin/export/audit-logs','audit_logs.csv')">Audit logs</button>
      </div>
    </div>` : ""}
  `;
}
async function doExport(path, name) {
  try { await downloadCsv(path, name); toast("Export downloaded."); }
  catch (e) { toast(e.message, true); }
}

/* ── audit ── */
async function loadAudit() {
  const logs = await api("/api/admin/audit-logs");
  const exp = ROLE === "PRIMARY_ADMIN" || ROLE === "SUPER_ADMIN";
  document.getElementById("main").innerHTML = `
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">Audit log</h2>
      ${exp ? `<button class="btn sm" onclick="doExport('/api/admin/export/audit-logs','audit_logs.csv')">Export CSV</button>` : ""}
    </div>
    <div class="card wrap" style="margin-top:16px"><table class="tbl"><thead><tr><th>Actor</th><th>Action</th><th>Entity</th><th>Detail</th><th>When</th></tr></thead>
      <tbody>${logs.map(a => `<tr><td class="mono" style="font-size:11px">${esc(a.actor_user_id||"system")}</td><td>${esc(a.action)}</td>
        <td class="mono">${esc(a.entity_type)} ${esc(a.entity_id)}</td><td style="max-width:280px;overflow:hidden;text-overflow:ellipsis">${esc(a.new_value)}</td><td>${fDateTime(a.timestamp)}</td></tr>`).join("") || '<tr><td colspan="5" style="color:var(--mute)">Nothing logged yet.</td></tr>'}</tbody></table></div>`;
}

/* ── notifications ── */
async function loadNotifications() {
  const ns = await api("/api/admin/notifications");
  document.getElementById("main").innerHTML = `
    <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Notifications</h2>
    <div class="grid" style="gap:10px">
      ${ns.map(n => `<div class="card pad" style="${n.is_read?'':'border-color:var(--flux)'}">
        <div style="display:flex;justify-content:space-between;gap:10px"><div class="disp" style="font-weight:600;font-size:14px">${esc(n.title)}</div>
        <span style="font-size:11px;color:var(--mute)">${fDateTime(n.created_at)}</span></div>
        <p style="color:var(--mute);font-size:13px;margin:6px 0 0">${esc(n.message)}</p>
        ${n.is_read?"":`<button class="btn sm" style="margin-top:8px" onclick="markRead('${n.id}')">Mark read</button>`}
      </div>`).join("") || '<span style="color:var(--mute)">No notifications yet.</span>'}
    </div>`;
}
async function markRead(id) {
  await api(`/api/admin/notifications/${id}/read`, { method: "POST" });
  loadNotifications();
}

function kv(label, val) { return `<div><div class="eyebrow">${esc(label)}</div><div class="mono" style="font-size:13.5px;margin-top:4px">${esc(val)}</div></div>`; }

async function togglePublic(id, makePublic) {
  try {
    await api(`/api/admin/projects/${id}/public`, { method: "POST", body: { is_public: makePublic } });
    toast(makePublic ? "Project is now public." : "Project unpublished.");
    loadProjects();
  } catch (e) { toast(e.message, true); }
}

/* ── warranty claims ── */
async function loadWarrantyClaims() {
  document.getElementById("main").innerHTML = loadingState("Loading warranty claims…");
  try {
    const [claims, wpanels] = await Promise.all([
      api("/api/admin/warranty/claims"),
      api("/api/admin/warranty/panels"),
    ]);
    const filter = window._wFilter || "";
    const q = (window._wQ || "").toLowerCase();
    const shown = claims.filter(c => {
      if (filter && c.status !== filter) return false;
      if (q && !(c.client_name + c.panel_serial + c.issue + c.id).toLowerCase().includes(q)) return false;
      return true;
    });
    const expiring = wpanels.filter(p => p.warranty_status === "EXPIRING_SOON").length;
    document.getElementById("main").innerHTML = `
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
        <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">Warranty claims</h2>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${canExport() ? `<button class="btn sm" onclick="doExport('/api/admin/export/warranty-claims','warranty_claims.csv')">Export CSV</button>` : ""}
          ${ROLE !== "ADMIN" ? `<button class="btn sm" onclick="runWarrantyScan()">Scan expiring</button>` : ""}
        </div>
      </div>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));margin:16px 0">
        ${kpi("Open claims", claims.filter(c => !["CLOSED","REJECTED"].includes(c.status)).length)}
        ${kpi("Expiring panels", expiring, "var(--flux)")}
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
        <input class="field" style="max-width:240px" placeholder="Search client, serial, issue…" value="${esc(window._wQ||"")}" oninput="window._wQ=this.value;loadWarrantyClaims()">
        <select class="field" style="max-width:220px" onchange="window._wFilter=this.value;loadWarrantyClaims()">
          <option value="">All statuses</option>
          ${["SUBMITTED","UNDER_REVIEW","MORE_INFORMATION_REQUIRED","APPROVED","REJECTED","REPLACEMENT_REQUIRED","REPLACED","REPAIRED","CLOSED"].map(s => `<option ${filter===s?"selected":""} value="${s}">${s.replace(/_/g," ")}</option>`).join("")}
        </select>
      </div>
      <div class="card wrap"><table class="tbl">
        <thead><tr><th>Claim</th><th>Client</th><th>Panel</th><th>Issue</th><th>Status</th><th>Opened</th><th></th></tr></thead>
        <tbody>${shown.map(c => `<tr>
          <td class="mono" style="font-size:11px">${esc(c.id)}</td>
          <td>${esc(c.client_name)}</td>
          <td class="mono">${esc(c.panel_serial)}</td>
          <td>${esc(c.issue)}</td>
          <td>${claimPill(c.status)}</td>
          <td>${fDate(c.created_at)}</td>
          <td><button class="btn sm" onclick="openClaim('${c.id}')">Open</button></td>
        </tr>`).join("") || `<tr><td colspan="7" style="color:var(--mute)">No warranty claims yet.</td></tr>`}</tbody>
      </table></div>`;
  } catch (e) {
    document.getElementById("main").innerHTML = errorState(e.message);
  }
}
async function runWarrantyScan() {
  try {
    const r = await api("/api/admin/warranty/scan-expiring", { method: "POST" });
    toast(`Scan complete. ${r.notified} new expiry alert(s).`);
  } catch (e) { toast(e.message, true); }
}
async function openClaim(id) {
  const c = await api("/api/admin/warranty/claims/" + id);
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:560px">
      <div class="sheet-hd"><div class="disp" style="font-weight:600">Claim ${esc(c.id)}</div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <div class="grid" style="grid-template-columns:1fr 1fr">
          ${kv("Client", c.client_name)} ${kv("Phone", c.client_phone || "—")}
          ${kv("Panel", c.panel_serial)} ${kv("Warranty", c.warranty_status)}
          ${kv("Issue", c.issue)} ${kv("Discovered", c.date_discovered || "—")}
        </div>
        <p style="color:var(--mute);font-size:13.5px;margin:12px 0">${esc(c.description || "")}</p>
        ${c.resolution_notes ? `<pre style="white-space:pre-wrap;font-size:12px;color:var(--mute)">${esc(c.resolution_notes)}</pre>` : ""}
        <label class="lab" style="margin-top:12px">Internal note</label>
        <textarea id="cl-notes" class="field" rows="2" placeholder="Visible to staff; sent to client with status change"></textarea>
        <label class="lab" style="margin-top:10px">Move to</label>
        ${c.allowed_next.length ? `<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px">
          ${c.allowed_next.map(s => `<button class="btn sm" onclick="changeClaim('${c.id}','${s}')">${s.replace(/_/g," ")}</button>`).join("")}
        </div>` : `<p style="color:var(--mute);font-size:13px">No further transitions.</p>`}
      </div>
    </div></div>`;
}
async function changeClaim(id, status) {
  if (!confirm(`Change claim to ${status.replace(/_/g," ")}?`)) return;
  const notes = (document.getElementById("cl-notes") || {}).value || "";
  try {
    await api(`/api/admin/warranty/claims/${id}/status`, { method: "POST", body: { status, notes } });
    document.getElementById("modal").innerHTML = "";
    toast("Claim updated.");
    loadWarrantyClaims();
  } catch (e) { toast(e.message, true); }
}

/* ── enquiries ── */
async function loadEnquiries() {
  try {
    const rows = await api("/api/admin/enquiries");
    window._enquiries = rows;
    document.getElementById("main").innerHTML = `
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 16px">Website enquiries</h2>
      <div class="card wrap"><table class="tbl">
        <thead><tr><th>When</th><th>Name</th><th>Email</th><th>Subject</th><th>Status</th><th></th></tr></thead>
        <tbody>${rows.map(e => `<tr>
          <td>${fDateTime(e.created_at)}</td><td>${esc(e.name)}</td><td>${esc(e.email)}</td>
          <td>${esc(e.subject)}</td><td>${claimPill(e.status)}</td>
          <td><button class="btn sm" onclick="openEnquiry('${e.id}')">Open</button></td>
        </tr>`).join("") || `<tr><td colspan="6" style="color:var(--mute)">No enquiries yet.</td></tr>`}</tbody>
      </table></div>`;
  } catch (e) { document.getElementById("main").innerHTML = errorState(e.message); }
}
function openEnquiry(id) {
  const e = (window._enquiries || []).find(x => x.id === id);
  if (!e) return;
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:520px">
      <div class="sheet-hd"><div class="disp" style="font-weight:600">${esc(e.subject || "Enquiry")}</div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        ${kv("From", e.name + " · " + e.email)} ${kv("Phone", e.phone || "—")}
        <p style="margin-top:12px;white-space:pre-wrap">${esc(e.message)}</p>
        <label class="lab" style="margin-top:12px">Internal notes</label>
        <textarea id="enq-notes" class="field" rows="2"></textarea>
        <label class="lab" style="margin-top:10px">Status</label>
        <select id="enq-st" class="field">
          ${["NEW","IN_PROGRESS","RESPONDED","CLOSED","SPAM"].map(s => `<option ${s===e.status?"selected":""}>${s}</option>`).join("")}
        </select>
        <button class="btn flux wide" style="margin-top:14px" onclick="saveEnquiry('${e.id}')">Save</button>
      </div>
    </div></div>`;
}
async function saveEnquiry(id) {
  try {
    await api(`/api/admin/enquiries/${id}/status`, { method: "POST", body: {
      status: document.getElementById("enq-st").value,
      internal_notes: document.getElementById("enq-notes").value,
    }});
    document.getElementById("modal").innerHTML = "";
    toast("Enquiry updated.");
    loadEnquiries();
  } catch (e) { toast(e.message, true); }
}

/* ── website CMS ── */
async function loadWebsiteCms() {
  try {
    const s = await api("/api/admin/settings");
    const fields = [
      ["company_name","Company name"],["company_phone","Phone"],["company_email","Email"],["company_address","Address"],
      ["support_email","Support email"],["support_phone","Support phone"],
      ["hero_heading","Hero heading"],["hero_description","Hero description"],["hero_cta","Hero CTA"],
      ["about_mission","Mission"],["about_vision","Vision"],["about_body","About story"],
      ["footer_text","Footer text"],
      ["social_linkedin","LinkedIn"],["social_instagram","Instagram"],["social_facebook","Facebook"],
      ["social_youtube","YouTube"],["social_x","X / Twitter"],
      ["seo_title","SEO title"],["seo_description","SEO description"],
      ["section_projects","Show projects (on/off)"],["section_services","Show services (on/off)"],
      ["section_faq","Show FAQ (on/off)"],["section_contact","Show contact (on/off)"],
    ];
    document.getElementById("main").innerHTML = `
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 8px">Website & branding</h2>
      <p style="color:var(--mute);margin:0 0 18px">These values drive the public site. Changes apply immediately.</p>
      <div class="card pad" style="margin-bottom:16px">
        <div class="disp" style="font-weight:600;margin-bottom:10px">Logo / favicon / hero</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          <div><label class="lab">Kind</label>
            <select id="br-kind" class="field"><option value="logo">Logo</option><option value="favicon">Favicon</option><option value="hero">Hero image</option></select></div>
          <input id="br-file" type="file" accept="image/*" class="field" style="max-width:240px">
          <button class="btn flux" onclick="uploadBrand()">Upload</button>
        </div>
        <div style="margin-top:10px;font-size:12.5px;color:var(--mute)">
          Logo: ${esc(s.brand_logo_url||"—")} · Favicon: ${esc(s.brand_favicon_url||"—")}
        </div>
      </div>
      <div class="card pad">
        ${fields.map(([k,l]) => `<label class="lab" for="set-${k}">${esc(l)}</label>
          ${k.includes("description") || k.includes("body") || k === "hero_description"
            ? `<textarea id="set-${k}" class="field" rows="3" style="margin-bottom:12px">${esc(s[k]||"")}</textarea>`
            : `<input id="set-${k}" class="field" style="margin-bottom:12px" value="${esc(s[k]||"")}">`}
        `).join("")}
        <button class="btn flux" onclick="saveWebsite()">Save website settings</button>
      </div>`;
  } catch (e) { document.getElementById("main").innerHTML = errorState(e.message); }
}
async function saveWebsite() {
  const payload = {};
  document.querySelectorAll("[id^='set-']").forEach(el => { payload[el.id.slice(4)] = el.value; });
  try {
    await api("/api/admin/settings", { method: "PUT", body: payload });
    await api("/api/admin/website-content", { method: "PUT", body: payload });
    toast("Website settings saved.");
  } catch (e) { toast(e.message, true); }
}
async function uploadBrand() {
  const file = document.getElementById("br-file").files[0];
  if (!file) { toast("Choose an image.", true); return; }
  const fd = new FormData();
  fd.append("kind", document.getElementById("br-kind").value);
  fd.append("file", file);
  try {
    const r = await apiUpload("/api/admin/branding/upload", fd);
    toast("Uploaded: " + r.url);
    loadWebsiteCms();
  } catch (e) { toast(e.message, true); }
}

/* ── FAQs ── */
async function loadFaqs() {
  try {
    const faqs = await api("/api/admin/faqs");
    window._faqs = faqs;
    document.getElementById("main").innerHTML = `
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px">
        <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">FAQs</h2>
        <button class="btn flux sm" onclick="openFaqForm()">+ Add FAQ</button>
      </div>
      <div class="card wrap" style="margin-top:16px"><table class="tbl">
        <thead><tr><th>#</th><th>Question</th><th>Category</th><th>Active</th><th></th></tr></thead>
        <tbody>${faqs.map(f => `<tr>
          <td>${f.sort_order}</td><td>${esc(f.question)}</td><td>${esc(f.category)}</td>
          <td>${f.is_active?"Yes":"No"}</td>
          <td><button class="btn sm" onclick="editFaq('${f.id}')">Edit</button>
            <button class="btn sm" onclick="toggleFaq('${f.id}', ${f.is_active? "false":"true"})">${f.is_active?"Archive":"Activate"}</button></td>
        </tr>`).join("") || `<tr><td colspan="5" style="color:var(--mute)">No FAQs yet.</td></tr>`}</tbody>
      </table></div>`;
  } catch (e) { document.getElementById("main").innerHTML = errorState(e.message); }
}
function editFaq(id) {
  const f = (window._faqs || []).find(x => x.id === id);
  openFaqForm(f || { question:"", answer:"", category:"GENERAL", sort_order:0, is_active:true });
}
function openFaqForm(f) {
  f = f || { question:"", answer:"", category:"GENERAL", sort_order:0, is_active:true };
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:520px">
      <div class="sheet-hd"><div class="disp" style="font-weight:600">${f.id?"Edit FAQ":"New FAQ"}</div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <label class="lab">Question</label><input id="fq-q" class="field" style="margin-bottom:10px" value="${esc(f.question||"")}">
        <label class="lab">Answer</label><textarea id="fq-a" class="field" rows="4" style="margin-bottom:10px">${esc(f.answer||"")}</textarea>
        <label class="lab">Category</label><input id="fq-c" class="field" style="margin-bottom:10px" value="${esc(f.category||"GENERAL")}">
        <label class="lab">Sort order</label><input id="fq-o" type="number" class="field" style="margin-bottom:14px" value="${f.sort_order||0}">
        <button class="btn flux wide" onclick="saveFaq('${f.id||""}')">Save</button>
      </div>
    </div></div>`;
}
async function saveFaq(id) {
  const body = {
    question: document.getElementById("fq-q").value.trim(),
    answer: document.getElementById("fq-a").value.trim(),
    category: document.getElementById("fq-c").value.trim(),
    sort_order: parseInt(document.getElementById("fq-o").value, 10) || 0,
    is_active: true,
  };
  try {
    if (id) await api("/api/admin/faqs/" + id, { method: "PUT", body });
    else await api("/api/admin/faqs", { method: "POST", body });
    document.getElementById("modal").innerHTML = "";
    toast("FAQ saved.");
    loadFaqs();
  } catch (e) { toast(e.message, true); }
}
async function toggleFaq(id, active) {
  await api("/api/admin/faqs/" + id, { method: "PUT", body: { is_active: active } });
  loadFaqs();
}

/* ── announcements ── */
async function loadAnnouncements() {
  try {
    const rows = await api("/api/admin/announcements");
    document.getElementById("main").innerHTML = `
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px">
        <h2 class="disp" style="font-size:24px;font-weight:600;margin:0">Announcements</h2>
        <button class="btn flux sm" onclick="openAnnForm()">+ New</button>
      </div>
      <div class="card wrap" style="margin-top:16px"><table class="tbl">
        <thead><tr><th>Title</th><th>Published</th><th>Dates</th><th></th></tr></thead>
        <tbody>${rows.map(a => `<tr>
          <td>${esc(a.title)}</td><td>${a.is_published?"Yes":"No"}</td>
          <td>${esc(a.start_date||"—")} → ${esc(a.end_date||"—")}</td>
          <td><button class="btn sm" onclick="toggleAnn('${a.id}', ${a.is_published? "false":"true"})">${a.is_published?"Unpublish":"Publish"}</button></td>
        </tr>`).join("") || `<tr><td colspan="4" style="color:var(--mute)">No announcements.</td></tr>`}</tbody>
      </table></div>`;
  } catch (e) { document.getElementById("main").innerHTML = errorState(e.message); }
}
function openAnnForm() {
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise">
      <div class="sheet-hd"><div class="disp" style="font-weight:600">New announcement</div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <label class="lab">Title</label><input id="an-t" class="field" style="margin-bottom:10px">
        <label class="lab">Message</label><textarea id="an-m" class="field" rows="3" style="margin-bottom:10px"></textarea>
        <label class="lab">CTA text</label><input id="an-c" class="field" style="margin-bottom:10px">
        <label class="lab">CTA URL</label><input id="an-u" class="field" style="margin-bottom:10px" placeholder="/login">
        <button class="btn flux wide" onclick="saveAnn()">Publish</button>
      </div>
    </div></div>`;
}
async function saveAnn() {
  try {
    await api("/api/admin/announcements", { method: "POST", body: {
      title: document.getElementById("an-t").value.trim(),
      message: document.getElementById("an-m").value.trim(),
      cta_text: document.getElementById("an-c").value.trim(),
      cta_url: document.getElementById("an-u").value.trim(),
      is_published: true,
    }});
    document.getElementById("modal").innerHTML = "";
    toast("Announcement published.");
    loadAnnouncements();
  } catch (e) { toast(e.message, true); }
}
async function toggleAnn(id, pub) {
  await api("/api/admin/announcements/" + id, { method: "PUT", body: { is_published: pub } });
  loadAnnouncements();
}

/* ── permission matrix (read-only) ── */
async function loadPermissions() {
  try {
    const d = await api("/api/admin/permissions/matrix");
    const roles = d.roles;
    const rows = Object.entries(d.matrix).map(([code, map]) => `<tr>
      <td class="mono" style="font-size:12px">${esc(code)}</td>
      ${roles.map(r => `<td style="text-align:center">${map[r] ? '<span style="color:var(--export)">✓</span>' : '<span style="color:var(--mute)">—</span>'}`).join("")}
    </tr>`).join("");
    document.getElementById("main").innerHTML = `
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 8px">Roles & permissions</h2>
      <p style="color:var(--mute);margin:0 0 16px">Read-only matrix. Backend authorization is authoritative. Editing permissions in-app is disabled to prevent self-escalation.</p>
      <div class="card wrap"><table class="tbl">
        <thead><tr><th>Permission</th>${roles.map(r => `<th>${r.replace("_"," ")}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table></div>`;
  } catch (e) { document.getElementById("main").innerHTML = errorState(e.message); }
}

/* ── system settings ── */
async function loadSettings() {
  try {
    const s = await api("/api/admin/settings");
    document.getElementById("main").innerHTML = `
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:0 0 8px">System settings</h2>
      <p style="color:var(--mute)">Primary Admin only. Warranty threshold and operational defaults.</p>
      <div class="card pad" style="max-width:480px;margin-top:16px">
        <label class="lab">Warranty expiring-soon window (days)</label>
        <input id="st-wdays" type="number" class="field" style="margin-bottom:14px" value="${esc(s.warranty_expiring_days||"90")}">
        <label class="lab">Primary color</label>
        <input id="st-pc" class="field" style="margin-bottom:14px" value="${esc(s.primary_color||"")}">
        <label class="lab">Accent color</label>
        <input id="st-ac" class="field" style="margin-bottom:14px" value="${esc(s.accent_color||"")}">
        <button class="btn flux" onclick="saveSysSettings()">Save</button>
      </div>`;
  } catch (e) { document.getElementById("main").innerHTML = errorState(e.message); }
}
async function saveSysSettings() {
  try {
    await api("/api/admin/settings", { method: "PUT", body: {
      warranty_expiring_days: document.getElementById("st-wdays").value,
      primary_color: document.getElementById("st-pc").value,
      accent_color: document.getElementById("st-ac").value,
    }});
    toast("Settings saved.");
  } catch (e) { toast(e.message, true); }
}

let _gsTimer;
function runGlobalSearch() {
  clearTimeout(_gsTimer);
  _gsTimer = setTimeout(async () => {
    const q = (document.getElementById("global-search") || {}).value || "";
    const box = document.getElementById("search-results");
    if (!box) return;
    if (q.trim().length < 2) { box.style.display = "none"; return; }
    try {
      const r = await api("/api/admin/search?q=" + encodeURIComponent(q.trim()));
      const blocks = [];
      if (r.clients.length) blocks.push(`<div class="eyebrow">Clients</div>` + r.clients.map(c => `<button class="rail-btn" onclick="openClientDetail('${c.id}');document.getElementById('search-results').style.display='none'">${esc(c.name)} <span class="mono" style="color:var(--mute)">${esc(c.phone||"")}</span></button>`).join(""));
      if (r.projects.length) blocks.push(`<div class="eyebrow" style="margin-top:8px">Projects</div>` + r.projects.map(p => `<div class="mono" style="padding:6px 12px">${esc(p.code)} · ${esc(p.name)}</div>`).join(""));
      if (r.panels.length) blocks.push(`<div class="eyebrow" style="margin-top:8px">Panels</div>` + r.panels.map(p => `<div class="mono" style="padding:6px 12px">${esc(p.serial)}</div>`).join(""));
      if (r.tickets.length) blocks.push(`<div class="eyebrow" style="margin-top:8px">Tickets</div>` + r.tickets.map(t => `<button class="rail-btn" onclick="openStaffTicket('${t.id}');document.getElementById('search-results').style.display='none'">${esc(t.subject)}</button>`).join(""));
      if (r.claims.length) blocks.push(`<div class="eyebrow" style="margin-top:8px">Claims</div>` + r.claims.map(c => `<button class="rail-btn" onclick="openClaim('${c.id}');document.getElementById('search-results').style.display='none'">${esc(c.issue)}</button>`).join(""));
      box.innerHTML = blocks.join("") || `<span style="color:var(--mute);font-size:13px">No matches.</span>`;
      box.style.display = "block";
    } catch (e) { box.style.display = "none"; }
  }, 250);
}
document.addEventListener("click", (e) => {
  const box = document.getElementById("search-results");
  if (box && !e.target.closest("#global-search") && !e.target.closest("#search-results")) box.style.display = "none";
});

boot();

