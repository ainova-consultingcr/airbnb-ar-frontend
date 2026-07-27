(function () {
  "use strict";

  const STORAGE_KEY = "avi_workshop_demo_v1";
  const money = new Intl.NumberFormat("es-CR", { style: "currency", currency: "CRC", maximumFractionDigits: 0 });
  const now = () => new Date().toISOString();
  const today = () => new Date().toLocaleDateString("es-CR", { day: "2-digit", month: "short", year: "numeric" });

  const seed = {
    requests: [
      { id: "SOL-1042", created: "22 jul 2026", customer: "María Rodríguez", phone: "8888-1204", vehicle: "Toyota Corolla 2012", plate: "BCR-417", mileage: "168,400 km", issue: "Ruido al frenar y vibración en el pedal", priority: "Alta", status: "Pendiente" },
      { id: "SOL-1041", created: "22 jul 2026", customer: "Carlos Méndez", phone: "8702-3310", vehicle: "Hyundai Accent 2017", plate: "CGH-902", mileage: "92,100 km", issue: "Mantenimiento preventivo de 90 mil km", priority: "Normal", status: "Diagnosticando" },
      { id: "SOL-1040", created: "21 jul 2026", customer: "Ana Solís", phone: "8311-4418", vehicle: "Toyota Hilux 2014", plate: "CL-7712", mileage: "214,800 km", issue: "Golpe en suspensión delantera", priority: "Normal", status: "Convertida" }
    ],
    orders: [
      { id: "OT-2087", requestId: "SOL-1040", customer: "Ana Solís", vehicle: "Toyota Hilux 2014", plate: "CL-7712", technician: "Diego Vargas", status: "En reparación", progress: 65, approved: true, diagnosis: "Amortiguadores delanteros con fuga y bujes fatigados.", labor: [{ description: "Cambio de amortiguadores delanteros", qty: 2, unit: 18500 }], parts: [{ description: "Amortiguador delantero reforzado", sku: "SUS-HIL-05-15-F", qty: 2, unit: 48500 }, { description: "Kit de bujes delanteros", sku: "BUJ-HIL-F", qty: 1, unit: 22000 }] },
      { id: "OT-2086", requestId: "SOL-1039", customer: "Luis Chaves", vehicle: "Nissan Sentra 2015", plate: "BCP-219", technician: "Sofía Mora", status: "Esperando aprobación", progress: 30, approved: false, diagnosis: "Pastillas delanteras al límite y discos con desgaste irregular.", labor: [{ description: "Servicio de frenos delanteros", qty: 1, unit: 28000 }], parts: [{ description: "Juego de pastillas delanteras", sku: "BRK-SEN-F", qty: 1, unit: 39000 }, { description: "Discos delanteros", sku: "DSC-SEN-F", qty: 2, unit: 42000 }] }
    ],
    invoices: [
      { id: "FAC-3091", orderId: "OT-2084", customer: "Jorge Araya", vehicle: "Honda Civic 2018", issued: "21 jul 2026", subtotal: 85000, tax: 11050, total: 96050, paid: 96050, status: "Pagada", method: "Tarjeta" },
      { id: "FAC-3090", orderId: "OT-2083", customer: "Laura Brenes", vehicle: "Toyota Yaris 2016", issued: "20 jul 2026", subtotal: 124000, tax: 16120, total: 140120, paid: 70000, status: "Pago parcial", method: "SINPE Móvil" }
    ]
  };

  let state;
  let activeTab = "requests";

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function load() {
    try { state = JSON.parse(localStorage.getItem(STORAGE_KEY)) || clone(seed); }
    catch (_) { state = clone(seed); }
  }
  function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
  }
  function orderSubtotal(order) {
    return [...(order.parts || []), ...(order.labor || [])].reduce((sum, item) => sum + Number(item.qty || 0) * Number(item.unit || 0), 0);
  }
  function nextId(prefix, collection) {
    const max = collection.reduce((n, item) => Math.max(n, Number(String(item.id).split("-")[1]) || 0), 0);
    return `${prefix}-${max + 1}`;
  }
  function badge(status) {
    const key = String(status).toLowerCase().replace(/\s+/g, "-").replace(/[ó]/g, "o");
    return `<span class="avi-ws-badge ${key}">${escapeHtml(status)}</span>`;
  }

  function styles() {
    const style = document.createElement("style");
    style.textContent = `
      #aviWorkshopLauncher{position:fixed;right:18px;top:18px;z-index:1000000;border:0;border-radius:999px;background:#f59e0b;color:#201300;font-weight:800;padding:12px 18px;box-shadow:0 10px 30px #0006;cursor:pointer}
      #aviWorkshop{position:fixed;inset:0;z-index:2000000;background:#07101f;color:#e5e7eb;font-family:Inter,system-ui,sans-serif;display:none;overflow:auto}
      #aviWorkshop.open{display:block}.avi-ws-shell{max-width:1440px;margin:auto;padding:22px}.avi-ws-top{display:flex;align-items:center;gap:14px;margin-bottom:20px}.avi-ws-logo{width:45px;height:45px;border-radius:14px;background:#f59e0b;color:#1f1300;display:grid;place-items:center;font-weight:900;font-size:20px}.avi-ws-top h1{font-size:20px;margin:0}.avi-ws-top p{margin:2px 0 0;color:#94a3b8;font-size:13px}.avi-ws-close{margin-left:auto;background:#172033;color:#fff;border:1px solid #334155;border-radius:10px;padding:9px 13px;cursor:pointer}
      .avi-ws-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}.avi-ws-kpi{background:#111a2c;border:1px solid #263249;border-radius:14px;padding:16px}.avi-ws-kpi small{color:#94a3b8}.avi-ws-kpi strong{display:block;font-size:26px;margin-top:5px}.avi-ws-kpi em{font-style:normal;color:#fbbf24;font-size:12px}
      .avi-ws-tabs{display:flex;gap:8px;border-bottom:1px solid #263249;margin-bottom:16px}.avi-ws-tab{border:0;background:transparent;color:#94a3b8;font-weight:700;padding:12px 15px;cursor:pointer;border-bottom:3px solid transparent}.avi-ws-tab.active{color:#fbbf24;border-color:#f59e0b}.avi-ws-toolbar{display:flex;gap:10px;justify-content:space-between;margin-bottom:14px}.avi-ws-toolbar input{min-width:260px;background:#101827;border:1px solid #334155;color:#fff;border-radius:9px;padding:10px}.avi-ws-primary,.avi-ws-action{border:0;border-radius:9px;font-weight:800;cursor:pointer}.avi-ws-primary{background:#f59e0b;color:#201300;padding:10px 14px}.avi-ws-action{background:#263249;color:#fff;padding:7px 10px;font-size:12px}.avi-ws-action.approve{background:#047857}.avi-ws-action.invoice{background:#2563eb}
      .avi-ws-card{background:#101827;border:1px solid #263249;border-radius:14px;overflow:hidden}.avi-ws-table{width:100%;border-collapse:collapse;font-size:13px}.avi-ws-table th{text-align:left;color:#94a3b8;background:#0d1523;padding:12px}.avi-ws-table td{padding:13px 12px;border-top:1px solid #263249;vertical-align:top}.avi-ws-table b{display:block;color:#fff}.avi-ws-muted{color:#94a3b8;font-size:12px}.avi-ws-badge{display:inline-block;padding:5px 8px;border-radius:999px;background:#334155;font-size:11px;font-weight:800}.avi-ws-badge.pendiente,.avi-ws-badge.esperando-aprobacion{background:#78350f;color:#fde68a}.avi-ws-badge.en-reparacion,.avi-ws-badge.diagnosticando,.avi-ws-badge.pago-parcial{background:#1e3a8a;color:#bfdbfe}.avi-ws-badge.pagada,.avi-ws-badge.convertida,.avi-ws-badge.finalizada{background:#064e3b;color:#a7f3d0}.avi-ws-progress{width:110px;height:7px;background:#334155;border-radius:9px;overflow:hidden;margin-top:6px}.avi-ws-progress i{display:block;height:100%;background:#f59e0b}
      .avi-ws-modal{position:fixed;inset:0;background:#000a;z-index:2100000;display:none;place-items:center;padding:20px}.avi-ws-modal.open{display:grid}.avi-ws-dialog{width:min(680px,100%);max-height:90vh;overflow:auto;background:#111a2c;border:1px solid #334155;border-radius:16px;padding:22px}.avi-ws-dialog h2{margin:0 0 18px}.avi-ws-form{display:grid;grid-template-columns:1fr 1fr;gap:12px}.avi-ws-field{display:flex;flex-direction:column;gap:5px}.avi-ws-field.full{grid-column:1/-1}.avi-ws-field label{font-size:12px;color:#94a3b8}.avi-ws-field input,.avi-ws-field select,.avi-ws-field textarea{background:#0b1220;border:1px solid #334155;color:#fff;border-radius:8px;padding:10px;font:inherit}.avi-ws-field textarea{min-height:80px}.avi-ws-dialog-actions{display:flex;justify-content:flex-end;gap:9px;margin-top:18px}.avi-ws-empty{padding:35px;text-align:center;color:#94a3b8}
      @media(max-width:800px){.avi-ws-kpis{grid-template-columns:1fr 1fr}.avi-ws-card{overflow:auto}.avi-ws-table{min-width:850px}.avi-ws-form{grid-template-columns:1fr}.avi-ws-field.full{grid-column:auto}#aviWorkshopLauncher{top:10px;right:10px}.avi-ws-shell{padding:14px}}
    `;
    document.head.appendChild(style);
  }

  function markup() {
    document.body.insertAdjacentHTML("beforeend", `
      <button id="aviWorkshopLauncher" type="button">🔧 Centro de Taller</button>
      <main id="aviWorkshop" aria-hidden="true">
        <div class="avi-ws-shell">
          <header class="avi-ws-top"><div class="avi-ws-logo">AVI</div><div><h1>Centro de Operaciones del Taller</h1><p>Repuestos Ruta 27 · Demo con datos simulados</p></div><button class="avi-ws-close" data-ws="close">Volver a AVI ✕</button></header>
          <section class="avi-ws-kpis" id="aviWsKpis"></section>
          <nav class="avi-ws-tabs">
            <button class="avi-ws-tab active" data-tab="requests">Solicitudes</button>
            <button class="avi-ws-tab" data-tab="orders">Órdenes de trabajo</button>
            <button class="avi-ws-tab" data-tab="invoices">Facturación</button>
          </nav>
          <section id="aviWsContent"></section>
        </div>
      </main>
      <div class="avi-ws-modal" id="aviWsModal"><div class="avi-ws-dialog" id="aviWsDialog"></div></div>
    `);
  }

  function renderKpis() {
    const pending = state.requests.filter(x => !["Convertida", "Cerrada"].includes(x.status)).length;
    const active = state.orders.filter(x => x.status !== "Finalizada").length;
    const receivable = state.invoices.reduce((sum, x) => sum + x.total - x.paid, 0);
    document.getElementById("aviWsKpis").innerHTML = `
      <div class="avi-ws-kpi"><small>Solicitudes abiertas</small><strong>${pending}</strong><em>requieren seguimiento</em></div>
      <div class="avi-ws-kpi"><small>Órdenes activas</small><strong>${active}</strong><em>en proceso del taller</em></div>
      <div class="avi-ws-kpi"><small>Esperando aprobación</small><strong>${state.orders.filter(x => !x.approved).length}</strong><em>cotizaciones enviadas</em></div>
      <div class="avi-ws-kpi"><small>Saldo por cobrar</small><strong>${money.format(receivable)}</strong><em>facturación simulada</em></div>`;
  }

  function toolbar(title, action) {
    return `<div class="avi-ws-toolbar"><input id="aviWsSearch" placeholder="Buscar cliente, vehículo, placa o número..."><button class="avi-ws-primary" data-ws="${action}">+ ${title}</button></div>`;
  }
  function renderRequests() {
    return toolbar("Nueva solicitud", "new-request") + `<div class="avi-ws-card"><table class="avi-ws-table"><thead><tr><th>Solicitud</th><th>Cliente</th><th>Vehículo</th><th>Necesidad</th><th>Prioridad</th><th>Estado</th><th></th></tr></thead><tbody>${state.requests.map(r => `<tr data-search="${escapeHtml(Object.values(r).join(" ").toLowerCase())}"><td><b>${r.id}</b><span class="avi-ws-muted">${r.created}</span></td><td><b>${escapeHtml(r.customer)}</b><span class="avi-ws-muted">${escapeHtml(r.phone)}</span></td><td><b>${escapeHtml(r.vehicle)}</b><span class="avi-ws-muted">${escapeHtml(r.plate)} · ${escapeHtml(r.mileage)}</span></td><td>${escapeHtml(r.issue)}</td><td>${badge(r.priority)}</td><td>${badge(r.status)}</td><td>${r.status !== "Convertida" ? `<button class="avi-ws-action" data-convert="${r.id}">Crear OT</button>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
  }
  function renderOrders() {
    return toolbar("Nueva orden", "new-order") + `<div class="avi-ws-card"><table class="avi-ws-table"><thead><tr><th>Orden</th><th>Cliente / vehículo</th><th>Diagnóstico</th><th>Técnico</th><th>Avance</th><th>Total estimado</th><th></th></tr></thead><tbody>${state.orders.map(o => `<tr data-search="${escapeHtml(Object.values(o).join(" ").toLowerCase())}"><td><b>${o.id}</b><span class="avi-ws-muted">${o.requestId || "Directa"}</span></td><td><b>${escapeHtml(o.customer)}</b><span class="avi-ws-muted">${escapeHtml(o.vehicle)} · ${escapeHtml(o.plate)}</span></td><td>${escapeHtml(o.diagnosis || "Pendiente de diagnóstico")}</td><td>${escapeHtml(o.technician || "Sin asignar")}</td><td>${badge(o.status)}<div class="avi-ws-progress"><i style="width:${o.progress || 0}%"></i></div></td><td><b>${money.format(orderSubtotal(o) * 1.13)}</b><span class="avi-ws-muted">IVA incluido</span></td><td>${!o.approved ? `<button class="avi-ws-action approve" data-approve="${o.id}">Aprobar</button>` : o.status !== "Finalizada" ? `<button class="avi-ws-action" data-advance="${o.id}">Avanzar</button>` : `<button class="avi-ws-action invoice" data-invoice="${o.id}">Facturar</button>`}</td></tr>`).join("")}</tbody></table></div>`;
  }
  function renderInvoices() {
    return toolbar("Nueva factura", "new-invoice") + `<div class="avi-ws-card"><table class="avi-ws-table"><thead><tr><th>Factura</th><th>Orden</th><th>Cliente</th><th>Emisión</th><th>Total</th><th>Pagado / saldo</th><th>Estado</th><th></th></tr></thead><tbody>${state.invoices.map(f => `<tr data-search="${escapeHtml(Object.values(f).join(" ").toLowerCase())}"><td><b>${f.id}</b></td><td>${f.orderId}</td><td><b>${escapeHtml(f.customer)}</b><span class="avi-ws-muted">${escapeHtml(f.vehicle)}</span></td><td>${f.issued}</td><td><b>${money.format(f.total)}</b><span class="avi-ws-muted">IVA ${money.format(f.tax)}</span></td><td>${money.format(f.paid)}<span class="avi-ws-muted">Saldo ${money.format(f.total - f.paid)}</span></td><td>${badge(f.status)}</td><td>${f.paid < f.total ? `<button class="avi-ws-action approve" data-pay="${f.id}">Registrar pago</button>` : `<button class="avi-ws-action" data-print="${f.id}">Ver comprobante</button>`}</td></tr>`).join("")}</tbody></table></div>`;
  }
  function render() {
    renderKpis();
    document.getElementById("aviWsContent").innerHTML = activeTab === "requests" ? renderRequests() : activeTab === "orders" ? renderOrders() : renderInvoices();
  }

  function openModal(html) { document.getElementById("aviWsDialog").innerHTML = html; document.getElementById("aviWsModal").classList.add("open"); }
  function closeModal() { document.getElementById("aviWsModal").classList.remove("open"); }
  function requestForm() {
    openModal(`<h2>Nueva solicitud de servicio</h2><form id="aviWsRequestForm" class="avi-ws-form">
      <div class="avi-ws-field"><label>Nombre del cliente</label><input name="customer" required value="Roberto Jiménez"></div><div class="avi-ws-field"><label>WhatsApp</label><input name="phone" required value="8890-2451"></div>
      <div class="avi-ws-field"><label>Vehículo</label><input name="vehicle" required value="Toyota Corolla 2016"></div><div class="avi-ws-field"><label>Placa</label><input name="plate" required value="BFG-625"></div>
      <div class="avi-ws-field"><label>Kilometraje</label><input name="mileage" value="124,500 km"></div><div class="avi-ws-field"><label>Prioridad</label><select name="priority"><option>Normal</option><option>Alta</option><option>Urgente</option></select></div>
      <div class="avi-ws-field full"><label>Problema o servicio solicitado</label><textarea name="issue" required>El aire acondicionado dejó de enfriar.</textarea></div>
      <div class="avi-ws-dialog-actions full"><button type="button" class="avi-ws-action" data-ws="dismiss">Cancelar</button><button class="avi-ws-primary">Registrar solicitud</button></div></form>`);
  }
  function convertRequest(id) {
    const r = state.requests.find(x => x.id === id); if (!r) return;
    r.status = "Convertida";
    state.orders.unshift({ id: nextId("OT", state.orders), requestId: r.id, customer: r.customer, vehicle: r.vehicle, plate: r.plate, technician: "Sin asignar", status: "Diagnóstico", progress: 10, approved: false, diagnosis: "Pendiente de inspección técnica.", labor: [{ description: "Diagnóstico general", qty: 1, unit: 18000 }], parts: [] });
    save(); activeTab = "orders"; syncTabs(); render();
  }
  function invoiceOrder(id) {
    const o = state.orders.find(x => x.id === id); if (!o) return;
    if (state.invoices.some(x => x.orderId === id)) { activeTab = "invoices"; syncTabs(); render(); return; }
    const subtotal = orderSubtotal(o), tax = Math.round(subtotal * .13);
    state.invoices.unshift({ id: nextId("FAC", state.invoices), orderId: o.id, customer: o.customer, vehicle: o.vehicle, issued: today(), subtotal, tax, total: subtotal + tax, paid: 0, status: "Pendiente", method: "" });
    save(); activeTab = "invoices"; syncTabs(); render();
  }
  function syncTabs() { document.querySelectorAll(".avi-ws-tab").forEach(x => x.classList.toggle("active", x.dataset.tab === activeTab)); }
  function receipt(id) {
    const f = state.invoices.find(x => x.id === id); if (!f) return;
    openModal(`<h2>Comprobante ${f.id}</h2><p><b>Repuestos Ruta 27</b><br><span class="avi-ws-muted">Factura demostrativa · No es comprobante fiscal</span></p><hr><p>Cliente: ${escapeHtml(f.customer)}<br>Vehículo: ${escapeHtml(f.vehicle)}<br>Orden: ${f.orderId}</p><h2>${money.format(f.total)}</h2><p>Subtotal: ${money.format(f.subtotal)}<br>IVA (13%): ${money.format(f.tax)}<br>Pagado: ${money.format(f.paid)}</p><div class="avi-ws-dialog-actions"><button class="avi-ws-primary" data-ws="dismiss">Cerrar</button></div>`);
  }

  function events() {
    document.addEventListener("click", e => {
      const t = e.target.closest("button"); if (!t) return;
      if (t.id === "aviWorkshopLauncher") { document.getElementById("aviWorkshop").classList.add("open"); render(); }
      if (t.dataset.ws === "close") document.getElementById("aviWorkshop").classList.remove("open");
      if (t.dataset.ws === "dismiss") closeModal();
      if (t.dataset.ws === "new-request") requestForm();
      if (t.dataset.ws === "new-order") { activeTab = "requests"; syncTabs(); render(); requestForm(); }
      if (t.dataset.ws === "new-invoice") { activeTab = "orders"; syncTabs(); render(); }
      if (t.dataset.tab) { activeTab = t.dataset.tab; syncTabs(); render(); }
      if (t.dataset.convert) convertRequest(t.dataset.convert);
      if (t.dataset.approve) { const o = state.orders.find(x => x.id === t.dataset.approve); o.approved = true; o.status = "Aprobada"; o.progress = 40; save(); render(); }
      if (t.dataset.advance) { const o = state.orders.find(x => x.id === t.dataset.advance); if (o.progress < 80) { o.progress = 85; o.status = "Control de calidad"; } else { o.progress = 100; o.status = "Finalizada"; } save(); render(); }
      if (t.dataset.invoice) invoiceOrder(t.dataset.invoice);
      if (t.dataset.pay) { const f = state.invoices.find(x => x.id === t.dataset.pay); f.paid = f.total; f.status = "Pagada"; f.method = "SINPE Móvil"; save(); render(); receipt(f.id); }
      if (t.dataset.print) receipt(t.dataset.print);
    });
    document.addEventListener("input", e => {
      if (e.target.id !== "aviWsSearch") return;
      const q = e.target.value.toLowerCase(); document.querySelectorAll("#aviWsContent tbody tr").forEach(row => row.hidden = !row.dataset.search.includes(q));
    });
    document.addEventListener("submit", e => {
      if (e.target.id !== "aviWsRequestForm") return; e.preventDefault();
      const d = Object.fromEntries(new FormData(e.target));
      state.requests.unshift({ id: nextId("SOL", state.requests), created: today(), customer: d.customer, phone: d.phone, vehicle: d.vehicle, plate: d.plate, mileage: d.mileage, issue: d.issue, priority: d.priority, status: "Pendiente", createdAt: now() });
      save(); closeModal(); activeTab = "requests"; syncTabs(); render();
    });
  }

  function init() {
    const config = typeof PROPERTY_CONFIG !== "undefined" ? PROPERTY_CONFIG : window.PROPERTY_CONFIG;
    if (config?.type !== "auto_parts_store") return false;
    load(); styles(); markup(); events(); render(); return true;
  }
  let attempts = 0;
  const timer = setInterval(() => { attempts += 1; if (init() || attempts > 50) clearInterval(timer); }, 200);
})();
