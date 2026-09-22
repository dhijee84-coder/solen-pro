let STATE = { tab: "home", overview: null, gen: null, bill_draft: null, reading: false, panels: [], claims: [] };

async function boot() {
  try {
    STATE.overview = await api("/api/client/me");
  } catch (e) {
    window.location.href = "/login";
    return;
  }
  document.getElementById("hdr-name").textContent = STATE.overview.user.name;
  document.getElementById("hdr-phone").textContent = "+91 " + (STATE.overview.user.phone || "");
  const ec = STATE.overview.electricity;
  if (ec && ec.rr_number) {
    const badge = document.getElementById("hdr-rr");
    badge.style.display = "inline";
    badge.textContent = `RR ${ec.rr_number} · ${ec.proposed_kw} kW`;
  }
  const unread = STATE.overview.unread_notifications || 0;
  if (unread) {
    const btn = document.getElementById("hdr-alert");
    btn.style.display = "inline-flex";
    btn.innerHTML = `${ico("bell",14)} ${unread} new`;
    btn.onclick = () => gotoTab("notifications");
  }
  if (!kycDone()) STATE.tab = "kyc";
  else if (!STATE.overview.project) STATE.tab = "bill";
  else STATE.tab = "home";
  render();
}

function kycDone() { return STATE.overview.profile.kyc_status === "VERIFIED"; }
function panDone() { return !!STATE.overview.profile.pan_number; }
function vis(key) {
  const v = STATE.overview.profile.visibility || {};
  return v[key] !== false;
}

function navItems() {
  const unread = STATE.overview.unread_notifications || 0;
  return [
    {id: "home", label: "Dashboard", icon: "trend", lock: false, show: true},
    {id: "kyc", label: "My profile", icon: "shield", lock: false, show: true},
    {id: "bill", label: "Connection", icon: "file", lock: !panDone(), show: true},
    {id: "project", label: "My project", icon: "activity", lock: !kycDone(), show: vis("show_project")},
    {id: "panels", label: "My panels", icon: "panel", lock: !kycDone(), show: vis("show_panels")},
    {id: "warranty", label: "Warranty", icon: "shield", lock: !kycDone(), show: vis("show_panels")},
    {id: "money", label: "Payments", icon: "wallet", lock: !kycDone(), show: vis("show_payments")},
    {id: "docs", label: "Documents", icon: "file", lock: !kycDone(), show: vis("show_documents")},
    {id: "gen", label: "Generation", icon: "trend", lock: !kycDone(), show: vis("show_generation")},
    {id: "services", label: "Services", icon: "settings", lock: !kycDone(), show: vis("show_services")},
    {id: "support", label: "Support", icon: "bell", lock: !kycDone(), show: vis("show_support")},
    {id: "notifications", label: unread ? `Alerts (${unread})` : "Notifications", icon: "bell", lock: false, show: vis("show_notifications")},
    {id: "settings", label: "Settings", icon: "settings", lock: false, show: true},
  ].filter(n => n.show);
}

function gotoTab(id) {
  STATE.tab = id;
  render();
  window.scrollTo(0, 0);
}

function render() {
  const paymentDueStage = (STATE.overview.stages || []).find(s => s.payment_status === "DUE");
  const alertBtn = document.getElementById("hdr-alert");
  if (paymentDueStage && STATE.tab !== "notifications") {
    alertBtn.style.display = "inline-flex";
    alertBtn.innerHTML = `${ico("bell",14)} Payment due`;
    alertBtn.onclick = () => gotoTab("project");
  }

  const nav = navItems();
  document.getElementById("rail-nav").innerHTML = nav.map(n => `
    <button class="rail-btn ${STATE.tab === n.id ? "on" : ""}" ${n.lock ? "disabled" : ""} onclick="gotoTab('${n.id}')">
      ${ico(n.lock ? "lock" : n.icon, 15)}<span style="flex:1">${n.label}</span>
    </button>`).join("");

  document.getElementById("rail-onboarding").innerHTML = [
    ["PAN verified", panDone()],
    ["Aadhaar verified", kycDone()],
    ["Bill uploaded", !!(STATE.overview.electricity && STATE.overview.electricity.rr_number)],
    ["Project assigned", !!STATE.overview.project],
  ].map(([t, v]) => `<div style="display:flex;align-items:center;gap:9px;padding:6px 12px;font-size:12.5px;color:${v ? "var(--export)" : "var(--mute)"}">
      ${ico(v ? "check" : "clock", 13)} ${t}</div>`).join("");

  const views = {
    home: viewHome, kyc: viewKyc, bill: viewBill, project: viewProject,
    panels: viewPanels, warranty: viewWarranty, money: viewMoney, docs: viewDocs,
    gen: viewGen, services: viewServices, support: viewSupport, notifications: viewNotifications,
    settings: viewSettings,
  };
  document.getElementById("main").innerHTML = (views[STATE.tab] || viewHome)();
  wireTabExtras();
}

function kv(label, val) {
  return `<div><div class="eyebrow">${esc(label)}</div><div class="mono" style="font-size:14px;margin-top:4px">${esc(val)}</div></div>`;
}

/* ── Dashboard ── */
function viewHome() {
  const o = STATE.overview;
  const w = o.warranty || {};
  const stages = o.stages || [];
  const done = stages.filter(s => s.status === "COMPLETED").length;
  const pct = stages.length ? Math.round(done / stages.length * 100) : 0;
  const current = stages.find(s => s.status === "IN_PROGRESS") || stages.find(s => s.status !== "COMPLETED");
  const paid = o.payments_total_paid || 0;
  const wLabel = w.expiring_soon ? `${w.expiring_soon} expiring soon` : (w.total ? `${w.active} active` : "No panels");
  return `<div class="rise" style="max-width:960px">
    <div class="eyebrow">Client portal</div>
    <h2 class="disp" style="font-size:28px;font-weight:600;margin:8px 0 4px">Welcome, ${esc(o.user.name)}</h2>
    <p style="color:var(--mute);margin:0 0 22px">${o.project ? esc(o.project.project_name) + " · " + o.project.allocated_capacity_kw + " kW allocated" : "Complete verification to receive panel allocation."}</p>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
      <div class="kpi"><div class="eyebrow">Project</div><div class="kpi-v">${o.project ? o.project.allocated_capacity_kw + " kW" : "—"}</div></div>
      <div class="kpi"><div class="eyebrow">Panels</div><div class="kpi-v">${o.project ? o.project.allocated_panels : 0}</div></div>
      <div class="kpi"><div class="eyebrow">Installation</div><div class="kpi-v">${pct}%</div></div>
      <div class="kpi"><div class="eyebrow">Paid</div><div class="kpi-v" style="color:var(--export)">${inr(paid)}</div></div>
      <div class="kpi"><div class="eyebrow">Warranty</div><div class="kpi-v" style="font-size:18px;${w.expiring_soon?'color:var(--flux)':''}">${esc(wLabel)}</div></div>
    </div>
    ${current ? `<div class="alertbar" style="margin-top:20px">
      <div><div class="eyebrow">Current stage</div><div class="disp" style="font-weight:600">${esc(current.stage_name)}</div>
      <div style="color:var(--mute);font-size:13px;margin-top:4px">${current.status.replace(/_/g," ")} · next: ${esc((stages.find(s => s.stage_number === current.stage_number + 1) || {}).stage_name || "Handover")}</div></div>
      <button class="btn sm flux" onclick="gotoTab('project')">Track installation</button>
    </div>` : ""}
    ${w.expiring_soon ? `<div class="alertbar" style="margin-top:12px">
      <div><div class="disp" style="font-weight:600">${w.expiring_soon} panel warranty expiring soon</div>
      <div style="color:var(--mute);font-size:13px">Review coverage and submit a claim if you have an issue.</div></div>
      <button class="btn sm" onclick="gotoTab('panels')">View warranty</button>
    </div>` : ""}
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr));margin-top:22px">
      <button class="card pad" style="text-align:left;cursor:pointer" onclick="gotoTab('panels')"><div class="eyebrow">Panels</div><div class="disp" style="font-weight:600;margin-top:6px">My panels</div><p style="color:var(--mute);font-size:13px;margin:6px 0 0">Serials, capacity and warranty status.</p></button>
      <button class="card pad" style="text-align:left;cursor:pointer" onclick="gotoTab('money')"><div class="eyebrow">Payments</div><div class="disp" style="font-weight:600;margin-top:6px">${inr(paid)} paid</div><p style="color:var(--mute);font-size:13px;margin:6px 0 0">History, receipts and upcoming dues.</p></button>
      <button class="card pad" style="text-align:left;cursor:pointer" onclick="gotoTab('gen')"><div class="eyebrow">Generation</div><div class="disp" style="font-weight:600;margin-top:6px">Energy dashboard</div><p style="color:var(--mute);font-size:13px;margin:6px 0 0">Daily, monthly and lifetime kWh.</p></button>
      <button class="card pad" style="text-align:left;cursor:pointer" onclick="gotoTab('support')"><div class="eyebrow">Support</div><div class="disp" style="font-weight:600;margin-top:6px">Open a ticket</div><p style="color:var(--mute);font-size:13px;margin:6px 0 0">Ask about installation, payments or warranty.</p></button>
    </div>
  </div>`;
}

/* ── KYC ── */
function viewKyc() {
  const p = STATE.overview.profile;
  const u = STATE.overview.user;
  return `<div class="rise" style="max-width:780px">
    <div class="eyebrow">Profile</div>
    <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Verify your identity</h2>
    <p style="color:var(--mute);font-size:14px;max-width:560px;margin-top:0">
      PAN and Aadhaar go on the net-metering agreement. Each is confirmed by OTP in this development build.</p>
    <div class="card pad" style="margin-top:18px">
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr))">
        ${kv("Name", u.name)} ${kv("Mobile", "+91 " + (u.phone||""))} ${kv("Email", u.email||"—")}
      </div>
    </div>
    <div class="card pad" style="margin-top:14px">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
        <div><div style="display:flex;align-items:center;gap:9px;color:var(--silver)">${ico("card",16)}
          <span class="disp" style="font-weight:600;font-size:16px;color:var(--ink)">PAN card</span></div>
          <p style="color:var(--mute);font-size:13px;margin:8px 0 0">Ten characters, exactly as printed on the card.</p></div>
        <span class="pill ${p.pan_number ? "p-done" : "p-due"}">${p.pan_number ? "Verified" : "Pending"}</span>
      </div>
      ${p.pan_number ? `<div class="mono" style="margin-top:16px;font-size:13px">${esc(p.pan_number)}</div>` : `
      <div style="display:flex;gap:12px;margin-top:16px;flex-wrap:wrap;align-items:flex-end">
        <div style="flex:1 1 240px">
          <label class="lab" for="f-pan">PAN number</label>
          <input id="f-pan" class="field mono" maxlength="10" placeholder="ABCDE1234F" style="letter-spacing:.14em;text-transform:uppercase">
        </div>
        <button class="btn flux" onclick="submitPan()">Verify</button>
      </div>
      <div class="err" id="pan-err"></div>`}
    </div>
    <div class="card pad" style="margin-top:14px;${panDone() ? "" : "opacity:.55;pointer-events:none"}">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
        <div><div style="display:flex;align-items:center;gap:9px;color:var(--silver)">${ico("shield",16)}
          <span class="disp" style="font-weight:600;font-size:16px;color:var(--ink)">Aadhaar card</span></div>
          <p style="color:var(--mute);font-size:13px;margin:8px 0 0">${panDone() ? "Twelve digits." : "Unlocks once PAN is verified."}</p></div>
        <span class="pill ${p.aadhaar_masked ? "p-done" : panDone() ? "p-due" : "p-lock"}">${p.aadhaar_masked ? "Verified" : panDone() ? "Pending" : "Locked"}</span>
      </div>
      ${p.aadhaar_masked ? `<div class="mono" style="margin-top:16px;font-size:13px">${esc(p.aadhaar_masked)}</div>` : `
      <div style="display:flex;gap:12px;margin-top:16px;flex-wrap:wrap;align-items:flex-end">
        <div style="flex:1 1 240px">
          <label class="lab" for="f-aad">Aadhaar number</label>
          <input id="f-aad" class="field mono" maxlength="12" inputmode="numeric" placeholder="1234 5678 9012" style="letter-spacing:.14em">
        </div>
        <button class="btn flux" onclick="submitAadhaar()">Verify</button>
      </div>
      <div class="err" id="aad-err"></div>`}
    </div>
  </div>`;
}

async function submitPan() {
  const v = document.getElementById("f-pan").value;
  try {
    await api("/api/client/kyc/pan", { method: "POST", body: { pan_number: v } });
    STATE.overview = await api("/api/client/me");
    toast("PAN verified.");
    render();
  } catch (e) { document.getElementById("pan-err").textContent = e.message; }
}
async function submitAadhaar() {
  const v = document.getElementById("f-aad").value;
  try {
    await api("/api/client/kyc/aadhaar", { method: "POST", body: { aadhaar_number: v } });
    STATE.overview = await api("/api/client/me");
    toast("Aadhaar verified.");
    render();
  } catch (e) { document.getElementById("aad-err").textContent = e.message; }
}

/* ── Bill / sizing ── */
function viewBill() {
  const ec = STATE.overview.electricity;
  if (ec && ec.rr_number) {
    return `<div class="rise" style="max-width:780px">
      <div class="eyebrow">Connection on file</div>
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Your electricity connection</h2>
      <div class="card pad grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-top:18px">
        ${kv("RR number", ec.rr_number)} ${kv("DISCOM", ec.discom)} ${kv("Tariff", ec.tariff)}
        ${kv("Sanctioned load", ec.sanctioned_load_kw + " kW")} ${kv("Avg. monthly units", ec.avg_monthly_units)}
        ${kv("Avg. monthly bill", inr(ec.avg_monthly_bill))} ${kv("Phase", ec.phase)}
      </div>
      <div class="card pad" style="margin-top:14px">
        <div class="disp" style="font-weight:600;font-size:16px;margin-bottom:10px">Proposed plant</div>
        <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
          ${kv("Capacity", ec.proposed_kw + " kW")} ${kv("System cost", inr(ec.system_cost))}
          ${kv("Subsidy estimate", inr(ec.subsidy_estimate))} ${kv("Payable", inr(ec.payable_amount))}
        </div>
      </div>
    </div>`;
  }
  if (STATE.reading) {
    return `<div class="rise" style="max-width:600px;text-align:center;padding-top:80px">
      ${ico("refresh", 22)} <span class="spin" style="display:inline-block"></span>
      <p style="color:var(--mute);margin-top:14px">Reading your electricity bill…</p></div>`;
  }
  if (STATE.bill_draft) {
    const d = STATE.bill_draft;
    return `<div class="rise" style="max-width:700px">
      <h2 class="disp" style="font-size:24px;font-weight:600;margin:8px 0">Review before saving</h2>
      <div class="card pad grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr))">
        ${kv("RR number", d.rr_number)} ${kv("DISCOM", d.discom)} ${kv("Tariff", d.tariff)}
        ${kv("Sanctioned load", d.sanctioned_load_kw + " kW")} ${kv("Avg. units/month", d.avg_monthly_units)}
        ${kv("Avg. bill/month", inr(d.avg_monthly_bill))}
      </div>
      <div class="card pad" style="margin-top:14px">
        <div class="disp" style="font-weight:600">Proposed ${d.proposed_kw} kW plant</div>
        <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:10px">
          ${kv("System cost", inr(d.system_cost))} ${kv("Subsidy est.", inr(d.subsidy_estimate))} ${kv("You pay", inr(d.payable_amount))}
        </div>
      </div>
      <div style="display:flex;gap:10px;margin-top:16px">
        <button class="btn flux" onclick="saveBill()">Confirm & save</button>
        <button class="btn" onclick="STATE.bill_draft=null;render()">Start over</button>
      </div>
    </div>`;
  }
  return `<div class="rise" style="max-width:600px">
    <div class="eyebrow">Step 2 of 3</div>
    <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Upload your electricity bill</h2>
    <p style="color:var(--mute);font-size:14px">We'll read your latest bill and propose a plant size.</p>
    <div class="drop" style="border:1px dashed var(--edge2);border-radius:4px;padding:30px 20px;text-align:center;background:rgba(18,41,67,.4);cursor:pointer" onclick="readBillSample()">
      ${ico("file", 22)}<p style="margin:10px 0 0;color:var(--mute)">Click to use a sample bill for this demo</p>
    </div>
  </div>`;
}

async function readBillSample() {
  STATE.reading = true; render();
  const units = 240 + Math.round(Math.random() * 400);
  setTimeout(async () => {
    STATE.reading = false;
    STATE.bill_draft = await api("/api/client/bill/draft", { method: "POST", body: {
      rr_number: "BNG-" + Math.floor(1000000 + Math.random() * 8999999),
      discom: "BESCOM", division: "South, Jayanagar sub-division",
      service_address: "No. 42, 3rd Cross, Jayanagar 4th Block, Bengaluru 560011",
      tariff: "LT-2(a) Domestic", avg_monthly_units: units,
    }});
    render();
  }, 1200);
}

async function saveBill() {
  await api("/api/client/bill/save", { method: "POST", body: STATE.bill_draft });
  STATE.bill_draft = null;
  STATE.overview = await api("/api/client/me");
  toast("Electricity bill recorded.");
  render();
}

/* ── Project stages ── */
function viewProject() {
  const stages = STATE.overview.stages || [];
  if (!stages.length) {
    return `<div class="rise" style="max-width:600px">${emptyState("No project yet", "Your project will appear here once an administrator allocates panel capacity.")}</div>`;
  }
  const current = stages.find(s => s.status === "IN_PROGRESS") || stages.find(s => s.status !== "COMPLETED");
  const next = current ? stages.find(s => s.stage_number === current.stage_number + 1) : null;
  const rows = stages.map((s) => {
    const flow = s.status === "COMPLETED";
    const nodeClass = s.status === "COMPLETED" ? "done" : s.status === "IN_PROGRESS" ? "live" : s.payment_status === "DUE" ? "due" : "";
    const pillClass = s.status === "COMPLETED" ? "p-done" : s.status === "IN_PROGRESS" ? "p-live" : s.payment_status === "DUE" ? "p-due" : "p-lock";
    return `<div class="bus-row">
      <div class="bus-gut ${flow ? "flow" : ""}"><div class="bus-node ${nodeClass}">${s.stage_number}</div></div>
      <div class="stage">
        <div class="stage-hd">
          <div>
            <div class="disp" style="font-weight:600;font-size:15.5px">${esc(s.stage_name)}</div>
            <div style="color:var(--mute);font-size:13px;margin-top:3px">${s.percentage}% of contract value</div>
          </div>
          <span class="pill ${pillClass}">${s.status.replace(/_/g," ")}</span>
        </div>
        ${s.payment_status === "DUE" ? `<button class="btn flux sm" style="margin-top:10px" onclick="openPay('${s.id}', ${STATE.overview.project ? STATE.overview.project.contract_total * s.percentage / 100 : 0})">Pay for this stage</button>` : ""}
        ${s.completed_at ? `<div style="color:var(--mute);font-size:12px;margin-top:8px">Completed ${fDate(s.completed_at)}</div>` : ""}
      </div>
    </div>`;
  }).join("");
  const pr = STATE.overview.project;
  return `<div class="rise" style="max-width:760px">
    <div class="eyebrow">Installation</div>
    <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">${esc(pr ? pr.project_name : "Project stages")}</h2>
    ${pr ? `<p style="color:var(--mute);font-size:14px">${esc(pr.project_code)} · ${pr.allocated_panels} panels · ${pr.allocated_capacity_kw} kW</p>` : ""}
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin:14px 0 8px">
      ${kv("Current stage", current ? current.stage_name : "Complete")}
      ${kv("Next stage", next ? next.stage_name : "—")}
      ${kv("Contract", pr ? inr(pr.contract_total) : "—")}
    </div>
    <div style="margin-top:10px">${rows}</div>
  </div>
  <div id="pay-modal"></div>`;
}

function openPay(stageId, amount) {
  document.getElementById("pay-modal").innerHTML = `
    <div class="modal-scrim" onclick="if(event.target===this) this.parentElement.innerHTML=''">
      <div class="sheet rise">
        <div class="sheet-hd"><div class="disp" style="font-weight:600">Pay ${inr(amount)}</div>
          <button class="btn sm bare" onclick="document.getElementById('pay-modal').innerHTML=''">✕</button></div>
        <div class="sheet-body">
          <label class="lab">Payment method</label>
          <div class="seg" style="margin-bottom:16px">
            <button class="on" id="pm-upi" onclick="setPm('upi')">UPI</button>
            <button id="pm-card" onclick="setPm('card')">Card</button>
            <button id="pm-nb" onclick="setPm('netbanking')">Net banking</button>
          </div>
          <button class="btn flux wide" onclick="settlePay('${stageId}', ${amount})">Pay ${inr(amount)}</button>
        </div>
      </div>
    </div>`;
}
let PM = "upi";
function setPm(m) { PM = m; document.querySelectorAll("#pay-modal .seg button").forEach(b => b.className = ""); document.getElementById("pm-" + (m === "netbanking" ? "nb" : m)).className = "on"; }

async function settlePay(stageId, amount) {
  await api("/api/client/payments/pay", { method: "POST", body: { amount, method: PM, stage_id: stageId } });
  document.getElementById("pay-modal").innerHTML = "";
  STATE.overview = await api("/api/client/me");
  toast("Payment successful.");
  render();
}

/* ── Panels ── */
function viewPanels() { return `<div class="rise" id="panels-root">${loadingState("Loading panels…")}</div>`; }
async function loadPanels() {
  const root = document.getElementById("panels-root");
  if (!root) return;
  try {
    STATE.panels = await api("/api/client/panels");
  } catch (e) {
    root.innerHTML = errorState(e.message || "Unable to load warranty information.");
    return;
  }
  const panels = STATE.panels;
  if (!panels.length) {
    root.innerHTML = `<h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">My panels</h2>${emptyState("No panels allocated", "Panels appear here after FIFO allocation to your project.")}`;
    return;
  }
  root.innerHTML = `
    <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">My panels</h2>
    <p style="color:var(--mute);margin:0 0 16px">${panels.length} allocated · warranty status from the server</p>
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr))">
      ${panels.map(p => `<div class="card pad">
        <div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">
          <div class="mono" style="font-size:13px">${esc(p.serial_number)}</div>
          ${warrantyPill(p.warranty_status)}
        </div>
        <div class="disp" style="font-weight:600;margin:10px 0 4px">${esc(p.manufacturer)} ${esc(p.model)}</div>
        <div style="color:var(--mute);font-size:13px">${p.watt_rating} W · ${esc(p.project_name || "")}</div>
        <div class="grid" style="grid-template-columns:1fr 1fr;margin-top:12px;gap:10px">
          ${kv("Install", p.installation_date || "—")} ${kv("Warranty end", p.warranty_end || "—")}
        </div>
        <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">
          <button class="btn sm" onclick="openPanelDetail('${p.id}')">Details</button>
          <button class="btn sm flux" onclick="openClaimForm('${p.id}')">Submit claim</button>
        </div>
      </div>`).join("")}
    </div>`;
}

function openPanelDetail(id) {
  const p = STATE.panels.find(x => x.id === id);
  if (!p) return;
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:520px">
      <div class="sheet-hd"><div class="disp" style="font-weight:600">Panel ${esc(p.serial_number)}</div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <div class="grid" style="grid-template-columns:1fr 1fr">
          ${kv("Manufacturer", p.manufacturer)} ${kv("Model", p.model)}
          ${kv("Wattage", p.watt_rating + " W")} ${kv("Status", p.status)}
          ${kv("Project", p.project_name || p.project_id)} ${kv("Install date", p.installation_date || "—")}
          ${kv("Warranty start", p.warranty_start || "—")} ${kv("Warranty end", p.warranty_end || "—")}
          ${kv("Type", p.warranty_type || "—")} ${kv("Provider", p.warranty_provider || "—")}
        </div>
        <div style="margin-top:12px">${warrantyPill(p.warranty_status)}</div>
        ${p.warranty_terms ? `<p style="color:var(--mute);font-size:13px;margin-top:12px">${esc(p.warranty_terms)}</p>` : ""}
        <button class="btn flux wide" style="margin-top:16px" onclick="document.getElementById('modal').innerHTML='';openClaimForm('${p.id}')">Submit warranty claim</button>
      </div>
    </div></div>`;
}

function openClaimForm(panelId) {
  const p = (STATE.panels || []).find(x => x.id === panelId);
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:520px">
      <div class="sheet-hd"><div class="disp" style="font-weight:600">Submit warranty claim</div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <label class="lab">Panel</label>
        <div class="mono" style="margin-bottom:12px">${esc(p ? p.serial_number : panelId)} ${p ? warrantyPill(p.warranty_status) : ""}</div>
        <label class="lab" for="cl-issue">Issue</label>
        <input id="cl-issue" class="field" style="margin-bottom:10px" placeholder="e.g. Reduced output / physical damage">
        <label class="lab" for="cl-desc">Description</label>
        <textarea id="cl-desc" class="field" rows="4" style="margin-bottom:10px" placeholder="What happened, and when did you notice it?"></textarea>
        <label class="lab" for="cl-date">Date discovered</label>
        <input id="cl-date" type="date" class="field" style="margin-bottom:14px">
        <div class="err" id="cl-err"></div>
        <button class="btn flux wide" onclick="submitClaim('${panelId}')">Submit claim</button>
      </div>
    </div></div>`;
}

async function submitClaim(panelId) {
  const issue = document.getElementById("cl-issue").value.trim();
  const description = document.getElementById("cl-desc").value.trim();
  const date_discovered = document.getElementById("cl-date").value;
  const err = document.getElementById("cl-err");
  if (issue.length < 5) { err.textContent = "Please describe the issue (at least 5 characters)."; return; }
  try {
    const r = await api("/api/client/warranty/claims", { method: "POST", body: {
      panel_id: panelId, issue_summary: issue, description, date_discovered,
    }});
    document.getElementById("modal").innerHTML = "";
    toast("Claim " + r.claim_id + " submitted.");
    STATE.overview = await api("/api/client/me");
    gotoTab("warranty");
  } catch (e) { err.textContent = e.message; }
}

/* ── Warranty claims ── */
function viewWarranty() { return `<div class="rise" id="warr-root">${loadingState("Loading claims…")}</div>`; }
async function loadWarranty() {
  const root = document.getElementById("warr-root");
  if (!root) return;
  try {
    STATE.claims = await api("/api/client/warranty/claims");
    if (!STATE.panels.length) STATE.panels = await api("/api/client/panels");
  } catch (e) {
    root.innerHTML = errorState(e.message);
    return;
  }
  const claims = STATE.claims;
  const filter = STATE.claimFilter || "ALL";
  const groups = {
    ALL: () => true,
    OPEN: c => !["CLOSED","REJECTED"].includes(c.status),
    IN_REVIEW: c => ["SUBMITTED","UNDER_REVIEW","MORE_INFORMATION_REQUIRED"].includes(c.status),
    APPROVED: c => ["APPROVED","REPLACEMENT_REQUIRED","REPLACED","REPAIRED"].includes(c.status),
    REJECTED: c => c.status === "REJECTED",
    CLOSED: c => c.status === "CLOSED",
  };
  const shown = claims.filter(groups[filter] || groups.ALL);
  const steps = ["SUBMITTED","UNDER_REVIEW","MORE_INFORMATION_REQUIRED","APPROVED","REPLACEMENT_REQUIRED","CLOSED"];
  root.innerHTML = `
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:0">My warranty claims</h2>
      <button class="btn flux sm" onclick="gotoTab('panels')">Claim from a panel</button>
    </div>
    <div class="seg" style="margin:16px 0">
      ${["ALL","OPEN","IN_REVIEW","APPROVED","REJECTED","CLOSED"].map(f =>
        `<button class="${filter===f?"on":""}" onclick="STATE.claimFilter='${f}';loadWarranty()">${f.replace("_"," ")}</button>`).join("")}
    </div>
    ${shown.length ? shown.map(c => {
      const idx = Math.max(0, steps.indexOf(c.status === "REJECTED" ? "UNDER_REVIEW" : c.status));
      const timeline = steps.map((st, i) => {
        const done = i < idx || c.status === st;
        const cur = c.status === st;
        return `<span class="pill ${cur?"p-due":done?"p-done":"p-lock"}" style="margin:2px">${st.replace(/_/g," ")}</span>`;
      }).join(" ");
      return `<div class="card pad" style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
          <div><div class="mono" style="font-size:12px">${esc(c.id)}</div>
            <div class="disp" style="font-weight:600;margin-top:4px">${esc(c.issue)}</div>
            <div style="color:var(--mute);font-size:13px;margin-top:4px">Panel ${esc(c.panel_serial || c.panel_id)} · ${fDate(c.created_at)}</div></div>
          ${claimPill(c.status)}
        </div>
        <div style="margin-top:12px">${timeline}</div>
        ${c.status === "REJECTED" && c.resolution_notes ? `<p style="color:var(--alert);font-size:13px;margin:10px 0 0">${esc(c.resolution_notes)}</p>` : ""}
        ${c.status === "MORE_INFORMATION_REQUIRED" ? `<p style="color:var(--flux);font-size:13px;margin:10px 0 0">${esc(c.resolution_notes || "Staff requested more information.")}</p>` : ""}
        ${c.description ? `<p style="color:var(--mute);font-size:13px;margin:10px 0 0">${esc(c.description)}</p>` : ""}
      </div>`;
    }).join("") : emptyState("No warranty claims yet", "Open a panel and submit a claim if you have an issue.")}`;
}

/* ── Payments ── */
async function viewMoney() { return `<div class="rise" id="money-root">${loadingState("Loading payments…")}</div>`; }
async function loadMoney() {
  const root = document.getElementById("money-root");
  if (!root) return;
  try {
    const pays = await api("/api/client/payments");
    const total = STATE.overview.project ? STATE.overview.project.contract_total : 0;
    const paid = pays.filter(p => p.status === "SUCCESS").reduce((s, p) => s + p.amount, 0);
    const pending = pays.filter(p => p.status === "PENDING");
    root.innerHTML = `
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Payments & history</h2>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-top:14px">
        <div class="kpi"><div class="eyebrow">Paid</div><div class="kpi-v" style="color:var(--export)">${inr(paid)}</div></div>
        <div class="kpi"><div class="eyebrow">Contract total</div><div class="kpi-v">${inr(total)}</div></div>
        <div class="kpi"><div class="eyebrow">Balance</div><div class="kpi-v">${inr(Math.max(0, total - paid))}</div></div>
      </div>
      <div class="card wrap" style="margin-top:20px">
        <table class="tbl">
          <thead><tr><th>Date</th><th>Reference</th><th>Method</th><th>Status</th><th class="rt">Amount</th></tr></thead>
          <tbody>${pays.map(p => `<tr><td>${fDate(p.created_at)}</td><td class="mono">${esc(p.txn||"—")}</td><td>${esc(p.method)}</td>
            <td><span class="pill ${p.status==="SUCCESS"?"p-done":"p-due"}">${p.status}</span></td><td class="rt mono">${inr(p.amount)}</td></tr>`).join("") || `<tr><td colspan="5" style="color:var(--mute)">No payments yet.</td></tr>`}</tbody>
        </table>
      </div>`;
  } catch (e) { root.innerHTML = errorState(e.message); }
}

/* ── Documents ── */
function viewDocs() { return `<div class="rise" id="docs-root">${loadingState("Loading documents…")}</div>`; }
async function loadDocs() {
  const root = document.getElementById("docs-root");
  if (!root) return;
  try {
    const docs = await api("/api/client/documents");
    root.innerHTML = `
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Documents</h2>
      <p style="color:var(--mute)">Upload permitted documents. Status is set by operations after review.</p>
      <div class="card pad" style="margin:14px 0">
        <label class="lab">Upload</label>
        <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end">
          <select id="doc-type" class="field" style="max-width:220px">
            ${["PAN","AADHAAR","ELECTRICITY_BILL","ADDRESS_PROOF","AGREEMENT","OTHER"].map(t=>`<option>${t}</option>`).join("")}
          </select>
          <input id="doc-file" type="file" class="field" style="max-width:280px" accept=".pdf,.png,.jpg,.jpeg,.webp">
          <button class="btn flux" onclick="uploadDoc()">Upload</button>
        </div>
        <div class="err" id="doc-err"></div>
      </div>
      <div class="card wrap">
        <table class="tbl"><thead><tr><th>Type</th><th>File</th><th>Status</th><th>Uploaded</th><th></th></tr></thead>
        <tbody>${docs.map(d => `<tr><td>${esc(d.type)}</td><td>${esc(d.filename||"—")}</td>
          <td><span class="pill ${d.status==="VERIFIED"?"p-done":d.status==="REJECTED"?"p-alert":"p-due"}">${d.status}</span></td>
          <td>${fDate(d.uploaded_at)}</td>
          <td><a class="btn sm" href="/api/client/documents/${esc(d.id)}/file" target="_blank" rel="noopener">Download</a></td></tr>`).join("") || `<tr><td colspan="5" style="color:var(--mute)">No documents yet.</td></tr>`}</tbody></table>
      </div>`;
  } catch (e) { root.innerHTML = errorState(e.message); }
}
async function uploadDoc() {
  const file = document.getElementById("doc-file").files[0];
  const err = document.getElementById("doc-err");
  err.textContent = "";
  if (!file) { err.textContent = "Choose a file."; return; }
  const fd = new FormData();
  fd.append("file", file);
  fd.append("document_type", document.getElementById("doc-type").value);
  try {
    await apiUpload("/api/client/documents/upload", fd);
    toast("Document uploaded.");
    loadDocs();
  } catch (e) { err.textContent = e.message; }
}

/* ── Generation ── */
async function viewGen() { return `<div class="rise" id="gen-root">${loadingState("Loading generation…")}</div>`; }
async function loadGen() {
  const root = document.getElementById("gen-root");
  if (!root) return;
  try {
    const g = await api("/api/client/generation");
    const recent = g.records.slice(-14);
    const max = Math.max(1, ...recent.map(r => r.kwh));
    const bars = recent.map(r => `<div title="${r.date}: ${r.kwh} kWh" style="flex:1;background:var(--flux);border-radius:2px 2px 0 0;height:${Math.max(4, (r.kwh/max)*140)}px"></div>`).join("");
    root.innerHTML = `
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Power generation</h2>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr));margin-top:14px">
        <div class="kpi"><div class="eyebrow">Today</div><div class="kpi-v">${g.today_kwh ?? 0} kWh</div></div>
        <div class="kpi"><div class="eyebrow">This week</div><div class="kpi-v">${g.this_week_kwh ?? 0} kWh</div></div>
        <div class="kpi"><div class="eyebrow">This month</div><div class="kpi-v">${g.this_month_kwh} kWh</div></div>
        <div class="kpi"><div class="eyebrow">Lifetime</div><div class="kpi-v">${g.lifetime_kwh} kWh</div></div>
        <div class="kpi"><div class="eyebrow">CO₂ avoided</div><div class="kpi-v" style="color:var(--export)">${g.lifetime_co2_kg} kg</div></div>
      </div>
      <div class="card pad" style="margin-top:20px">
        <div class="eyebrow" style="margin-bottom:12px">Last 14 days</div>
        <div style="display:flex;gap:6px;align-items:flex-end;height:150px">${bars || '<span style="color:var(--mute)">No generation recorded yet.</span>'}</div>
      </div>`;
  } catch (e) { root.innerHTML = errorState(e.message); }
}

/* ── Services ── */
async function viewServices() { return `<div class="rise" id="svc-root">${loadingState("Loading services…")}</div>`; }
async function loadServices() {
  const root = document.getElementById("svc-root");
  if (!root) return;
  try {
    const [catalog, myReqs] = await Promise.all([
      api("/api/client/services/catalog"), api("/api/client/services/my-requests"),
    ]);
    root.innerHTML = `
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Services</h2>
      <p style="color:var(--mute);margin:0 0 16px">Request cleaning, inspection or other work on your allocated system.</p>
      <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))">
        ${catalog.map(s => `<div class="card pad">
          <div style="font-weight:600">${esc(s.name)}</div>
          <div style="color:var(--mute);font-size:12.5px;margin:6px 0">${esc(s.description||"")}</div>
          <div class="mono" style="margin-bottom:10px">${s.base_price ? inr(s.base_price) : "Quote on request"}</div>
          <button class="btn sm" onclick="requestService('${s.id}')">Request</button>
        </div>`).join("") || emptyState("No services published yet", "Check back later.")}
      </div>
      ${myReqs.length ? `<div class="card wrap" style="margin-top:16px"><table class="tbl"><thead><tr><th>Service</th><th>Status</th><th>Quoted</th><th>Opened</th></tr></thead>
        <tbody>${myReqs.map(r => `<tr><td>${esc(r.service)}</td><td>${claimPill(r.status)}</td><td>${r.quoted_price ? inr(r.quoted_price) : "—"}</td><td>${fDate(r.created_at)}</td></tr>`).join("")}</tbody></table></div>` : ""}`;
  } catch (e) { root.innerHTML = errorState(e.message); }
}
async function requestService(serviceId) {
  await api("/api/client/services/request", { method: "POST", body: { service_id: serviceId } });
  toast("Service requested.");
  loadServices();
}

/* ── Support tickets ── */
function viewSupport() { return `<div class="rise" id="sup-root">${loadingState("Loading tickets…")}</div>`; }
async function loadSupport() {
  const root = document.getElementById("sup-root");
  if (!root) return;
  try {
    const tickets = await api("/api/client/tickets");
    root.innerHTML = `
      <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Support</h2>
      <p style="color:var(--mute);margin:0 0 16px">Open a ticket and follow the conversation with operations.</p>
      <div class="card pad" style="margin-bottom:16px">
        <div class="disp" style="font-weight:600;margin-bottom:10px">New ticket</div>
        <label class="lab">Subject</label>
        <input id="tk-subject" class="field" style="margin-bottom:10px" placeholder="Installation status enquiry">
        <div class="grid" style="grid-template-columns:1fr 1fr;margin-bottom:10px">
          <div><label class="lab">Category</label>
            <select id="tk-cat" class="field"><option>GENERAL</option><option>INSTALLATION</option><option>BILLING</option><option>WARRANTY</option><option>GENERATION</option></select></div>
          <div><label class="lab">Priority</label>
            <select id="tk-pri" class="field"><option>NORMAL</option><option>MEDIUM</option><option>HIGH</option></select></div>
        </div>
        <label class="lab">Description</label>
        <textarea id="tk-desc" class="field" rows="3" style="margin-bottom:12px" placeholder="Share enough detail for the team to help."></textarea>
        <button class="btn flux" onclick="createTicket()">Submit ticket</button>
      </div>
      <div class="card wrap"><table class="tbl"><thead><tr><th>Subject</th><th>Category</th><th>Status</th><th>Opened</th><th></th></tr></thead>
        <tbody>${tickets.map(t => `<tr><td>${esc(t.subject)}</td><td>${esc(t.category||"")}</td><td>${claimPill(t.status)}</td><td>${fDate(t.created_at)}</td>
          <td><button class="btn sm" onclick="openClientTicket('${t.id}')">View</button></td></tr>`).join("") || '<tr><td colspan="5" style="color:var(--mute)">No tickets yet.</td></tr>'}</tbody></table></div>`;
  } catch (e) { root.innerHTML = errorState(e.message); }
}
async function createTicket() {
  const subject = document.getElementById("tk-subject").value.trim();
  const description = document.getElementById("tk-desc").value.trim();
  if (!subject) { toast("Enter a subject.", true); return; }
  await api("/api/client/tickets", { method: "POST", body: {
    subject, description, category: document.getElementById("tk-cat").value, priority: document.getElementById("tk-pri").value,
  }});
  toast("Ticket submitted.");
  loadSupport();
}
async function openClientTicket(id) {
  const t = await api("/api/client/tickets/" + id);
  document.getElementById("modal").innerHTML = `<div class="modal-scrim" onclick="if(event.target===this)this.parentElement.innerHTML=''">
    <div class="sheet rise" style="max-width:520px">
      <div class="sheet-hd"><div><div class="disp" style="font-weight:600">${esc(t.subject)}</div>
        <div style="margin-top:4px">${claimPill(t.status)}</div></div>
        <button class="btn sm bare" onclick="document.getElementById('modal').innerHTML=''">✕</button></div>
      <div class="sheet-body">
        <p style="color:var(--mute);font-size:13.5px">${esc(t.description || "No description.")}</p>
        <div style="margin:14px 0;display:flex;flex-direction:column;gap:8px">
          ${(t.messages||[]).map(m => `<div class="card pad" style="padding:10px 12px;${m.mine?'border-color:var(--flux)':''}">
            <div style="font-size:11px;color:var(--mute)">${m.mine?"You":"Staff"} · ${fDateTime(m.created_at)}</div>
            <div style="margin-top:4px">${esc(m.message)}</div>
          </div>`).join("") || '<span style="color:var(--mute);font-size:13px">No replies yet.</span>'}
        </div>
        <textarea id="tk-reply" class="field" rows="2" placeholder="Reply…"></textarea>
        <button class="btn flux wide" style="margin-top:10px" onclick="replyClientTicket('${t.id}')">Send reply</button>
      </div>
    </div></div>`;
}
async function replyClientTicket(id) {
  const message = document.getElementById("tk-reply").value.trim();
  if (!message) return;
  await api(`/api/client/tickets/${id}/messages`, { method: "POST", body: { message } });
  toast("Reply sent.");
  openClientTicket(id);
}

function viewSettings() {
  const u = STATE.overview.user;
  const p = STATE.overview.profile;
  return `<div class="rise" style="max-width:640px">
    <h2 class="disp" style="font-size:27px;font-weight:600;margin:8px 0">Settings</h2>
    <div class="card pad">
      <div class="grid" style="grid-template-columns:1fr 1fr">
        ${kv("Name", u.name)} ${kv("Mobile", "+91 " + (u.phone||""))}
        ${kv("Email", u.email||"—")} ${kv("KYC", p.kyc_status)}
      </div>
      <p style="color:var(--mute);font-size:13px;margin:16px 0 0">Client accounts use OTP sign-in. Profile identity is locked after KYC verification.</p>
      <button class="btn" style="margin-top:16px" onclick="logout()">Sign out</button>
    </div>
  </div>`;
}

/* ── Notifications ── */
function viewNotifications() { return `<div class="rise" id="ntf-root">${loadingState("Loading notifications…")}</div>`; }
async function loadNotifications() {
  const root = document.getElementById("ntf-root");
  if (!root) return;
  try {
    const ns = await api("/api/client/notifications");
    const filter = STATE.ntfFilter || "ALL";
    const shown = ns.filter(n => filter === "ALL" || (filter === "UNREAD" ? !n.is_read : (n.type || "").includes(filter)));
    root.innerHTML = `
      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
        <h2 class="disp" style="font-size:27px;font-weight:600;margin:0">Notifications</h2>
        <button class="btn sm" onclick="markAllRead()">Mark all read</button>
      </div>
      <div class="seg" style="margin:16px 0">
        ${[["ALL","All"],["UNREAD","Unread"],["PAYMENT","Payments"],["WARRANTY","Warranty"],["INSTALLATION","Install"]].map(([k,l]) =>
          `<button class="${filter===k?"on":""}" onclick="STATE.ntfFilter='${k}';loadNotifications()">${l}</button>`).join("")}
      </div>
      <div class="grid" style="gap:10px">
        ${shown.map(n => `<div class="card pad" style="${n.is_read?'':'border-color:var(--flux)'}">
          <div style="display:flex;justify-content:space-between;gap:10px"><div class="disp" style="font-weight:600;font-size:14px">${esc(n.title)}</div>
          <span style="font-size:11px;color:var(--mute)">${fDateTime(n.created_at)}</span></div>
          <p style="color:var(--mute);font-size:13px;margin:6px 0 0">${esc(n.message)}</p>
          ${n.is_read?"":`<button class="btn sm" style="margin-top:8px" onclick="markClientRead('${n.id}')">Mark read</button>`}
        </div>`).join("") || emptyState("No notifications", "You'll see payments, installation and warranty updates here.")}
      </div>`;
  } catch (e) { root.innerHTML = errorState(e.message); }
}
async function markClientRead(id) {
  await api(`/api/client/notifications/${id}/read`, { method: "POST" });
  STATE.overview = await api("/api/client/me");
  loadNotifications();
}
async function markAllRead() {
  await api("/api/client/notifications/read-all", { method: "POST" });
  STATE.overview = await api("/api/client/me");
  toast("All notifications marked read.");
  loadNotifications();
}

function wireTabExtras() {
  if (STATE.tab === "money") loadMoney();
  if (STATE.tab === "gen") loadGen();
  if (STATE.tab === "services") loadServices();
  if (STATE.tab === "panels") loadPanels();
  if (STATE.tab === "warranty") loadWarranty();
  if (STATE.tab === "docs") loadDocs();
  if (STATE.tab === "notifications") loadNotifications();
  if (STATE.tab === "support") loadSupport();
}

boot();
