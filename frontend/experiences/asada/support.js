/* AVI ASADA support: AVI users and role-scoped operational context. */
(() => {
  const panel = document.getElementById("asadaSupportPanel");
  if (!panel) return;
  const tokenKey = `avi_asada_token_${CURRENT_PROPERTY}`;
  const basePath = `${API_BASE_URL}/asadas/${encodeURIComponent(CURRENT_PROPERTY)}/support`;
  const loginForm = document.getElementById("aviAsadaLogin");
  const session = document.getElementById("aviAsadaSession");
  const message = document.getElementById("aviAsadaMessage");
  const logoutButton = document.getElementById("aviAsadaLogout");
  let token = sessionStorage.getItem(tokenKey) || "";
  let currentUser = null;
  let setupRequired = false;
  let refreshTimer = null;
  let notificationRegistration = null;
  let pushSubscribed = false;
  let contextInitialized = false;
  let activeCriticalNodes = new Set();
  let requestedOrderId = new URLSearchParams(location.search).get("order");
  let orderInteractionUntil = 0;
  const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);
  const formatDateTime = value => {
    if (!value) return "Hora no disponible";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Hora no disponible" : date.toLocaleString([], {dateStyle:"short", timeStyle:"medium"});
  };

  async function request(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${basePath}${path}`, {...options, headers});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "AVI no pudo completar la consulta.");
    return data;
  }

  window.AVIExperienceExtensions?.register("assistant:ask", "asada-support", async ({question}) => {
    if (!token || !currentUser) {
      return {handled:true, answer:"Inicia sesión con tu usuario de AVI para consultar la operación de esta ASADA."};
    }
    try {
      const result = await request("/ask", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({question,period_days:30})
      });
      return {handled:true, answer:result.answer};
    } catch (error) {
      return {handled:true, answer:error.message};
    }
  });

  function showLogin(setup = false, text = "") {
    setupRequired = setup;
    panel.classList.add("asada-login-gate");
    document.body.classList.add("asada-auth-required");
    loginForm.hidden = false; session.hidden = true; logoutButton.hidden = true;
    for (const name of ["full_name", "setup_key"]) {
      loginForm.elements[name].hidden = !setup;
      loginForm.elements[name].required = setup;
    }
    loginForm.querySelector("button").textContent = setup ? "Crear administrador AVI" : "Ingresar";
    message.textContent = text;
  }

  function showSession(user) {
    currentUser = user;
    panel.classList.remove("asada-login-gate");
    document.body.classList.remove("asada-auth-required");
    loginForm.hidden = true; session.hidden = false; logoutButton.hidden = false;
    document.getElementById("aviAsadaUser").textContent = `${user.full_name} · ${user.role}`;
    document.getElementById("aviAsadaSummary").hidden = !user.permissions.includes("summary");
    document.getElementById("aviAsadaUsers").hidden = !user.permissions.includes("users");
    contextInitialized = false;
    activeCriticalNodes = new Set();
    renderAlertHistory();
    prepareNotifications();
    clearInterval(refreshTimer);
    refreshTimer = setInterval(loadContext, Math.max(3, Number(PROPERTY_CONFIG?.asada?.refresh_seconds || 3)) * 1000);
  }

  function logout(text = "") {
    token = ""; currentUser = null; contextInitialized = false; activeCriticalNodes = new Set(); clearInterval(refreshTimer); refreshTimer = null;
    sessionStorage.removeItem(tokenKey); showLogin(false, text);
  }

  async function loadContext() {
    message.textContent = "AVI está consultando la operación de la ASADA…";
    try {
      const context = await request("/context");
      handleCriticalAlerts(context.anomalies || []);
      document.getElementById("aviAsadaAnomalies").innerHTML = context.anomalies.length ? context.anomalies.map(item =>
        `<article class="asada-node"><div class="asada-node-heading"><strong>${escapeHtml(item.sector)} · ${escapeHtml(item.node_id)}</strong><time datetime="${escapeHtml(item.timestamp || "")}">${escapeHtml(formatDateTime(item.timestamp))}</time></div><span>Presión: ${item.pressure_psi ?? "—"} psi · Caudal: ${item.flow_lpm ?? "—"} L/min</span><span class="asada-state ${escapeHtml(String(item.severity).toLowerCase())}">${escapeHtml(item.severity)}</span><p>${escapeHtml(item.explanation)}</p></article>`
      ).join("") : '<article class="asada-node"><strong>Sin anomalías activas</strong><p>AVI no encontró condiciones fuera de rango en los datos disponibles.</p></article>';
      if (Date.now() >= orderInteractionUntil) renderOrders(context.orders || []);
      if (currentUser.permissions.includes("summary")) {
        const summary = await request("/summary?period_days=30");
        document.getElementById("aviAsadaSummary").innerHTML = `<strong>Resumen de los últimos ${summary.period_days} días</strong><span>${summary.total_failures} averías registradas</span><span>Sector con más averías: ${escapeHtml(summary.top_sector || "Sin datos")} (${summary.top_sector_failures})</span><span>Causa principal: ${escapeHtml(summary.main_cause || "Sin diagnósticos")}</span>`;
      }
      if (currentUser.permissions.includes("users")) await loadUsers();
      message.textContent = "Información actualizada con datos de la API de la ASADA.";
    } catch (error) {
      if (/sesión|session|login/i.test(error.message)) logout(error.message);
      else message.textContent = error.message;
    }
  }

  async function loadUsers() {
    const users = await request("/users");
    document.getElementById("aviAsadaUserList").innerHTML = users.map(user => `<span>${escapeHtml(user.full_name)} · ${escapeHtml(user.role)} · ${escapeHtml(user.username)}</span>`).join("");
  }

  function renderOrders(orders) {
    const host = document.getElementById("aviAsadaOrderList");
    host.innerHTML = orders.length ? orders.map(order => {
      const assignedToMe = String(order.assignee || "").toLowerCase() === String(currentUser?.username || "").toLowerCase();
      const open = !["RESUELTA", "DESCARTADA"].includes(order.status);
      const actions = currentUser?.role !== "FONTANERO" || !open ? "" : !order.assignee
        ? `<button class="asada-order-claim" type="button" data-order-id="${order.id}" data-updated-at="${escapeHtml(order.updated_at)}">Tomar orden</button>`
        : assignedToMe ? `<form class="asada-order-form" data-order-id="${order.id}" data-updated-at="${escapeHtml(order.updated_at)}">
            <select name="status" aria-label="Estado"><option value="EN ATENCION">En atención</option><option value="RESUELTA">Resuelta</option></select>
            <select name="diagnosis" aria-label="Diagnóstico"><option value="SIN CONFIRMAR">Sin confirmar</option><option value="FUGA CONFIRMADA">Fuga confirmada</option><option value="CONEXION NO AUTORIZADA CONFIRMADA">Conexión no autorizada</option><option value="OTRA CAUSA">Otra causa</option></select>
            <textarea name="note" placeholder="Nota de la inspección" required minlength="3"></textarea>
            <button type="submit">Guardar atención</button>
          </form>` : "";
      return `<article class="asada-order" id="avi-order-${order.id}">
        <div class="asada-order-title"><strong>OT-${String(order.id).padStart(5,"0")} · ${escapeHtml(order.node_id)}</strong><span class="asada-order-status">${escapeHtml(order.status)}</span></div>
        <time>${escapeHtml(formatDateTime(order.created_at))}</time>
        <span>Presión: ${order.pressure_psi ?? "—"} psi · Caudal: ${order.flow_lpm ?? "—"} L/min</span>
        <span>Responsable: ${escapeHtml(order.assignee || "Sin asignar")}</span>
        <span>Diagnóstico: ${escapeHtml(order.diagnosis || "SIN CONFIRMAR")}</span>${actions}</article>`;
    }).join("") : "<p>No hay órdenes visibles para tu perfil.</p>";
    if (requestedOrderId) {
      const target = document.getElementById(`avi-order-${requestedOrderId}`);
      if (target) {
        target.classList.add("asada-order-target");
        target.scrollIntoView({behavior:"smooth", block:"center"});
        requestedOrderId = null;
      }
    }
  }

  function alertStorageKey() {
    return `avi_asada_alerts_${CURRENT_PROPERTY}_${currentUser?.username || "anonymous"}`;
  }

  function savedAlerts() {
    try { return JSON.parse(localStorage.getItem(alertStorageKey()) || "[]"); }
    catch { return []; }
  }

  function renderAlertHistory() {
    const host = document.getElementById("aviAsadaAlertHistory");
    if (!host || !currentUser) return;
    const alerts = savedAlerts().slice(0, 8);
    host.innerHTML = alerts.length ? alerts.map(alert => `<article><strong>${escapeHtml(alert.sector)} · ${escapeHtml(alert.node_id)}</strong><time>${escapeHtml(formatDateTime(alert.timestamp))}</time><span>${escapeHtml(alert.message)}</span></article>`).join("") : "<p>Sin alertas nuevas registradas en este dispositivo.</p>";
  }

  function handleCriticalAlerts(anomalies) {
    const critical = anomalies.filter(item => ["CRITICA", "CRITICAL", "POSSIBLE_LEAK", "POSIBLE FUGA"].includes(String(item.severity).toUpperCase()));
    const current = new Set(critical.map(item => String(item.node_id)));
    if (contextInitialized) {
      for (const item of critical) {
        if (!activeCriticalNodes.has(String(item.node_id))) recordCriticalAlert(item);
      }
    }
    activeCriticalNodes = current;
    contextInitialized = true;
  }

  function recordCriticalAlert(item) {
    const alert = {
      node_id:String(item.node_id || "Sin nodo"),
      sector:String(item.sector || "Sin sector"),
      timestamp:item.timestamp || new Date().toISOString(),
      message:`Posible fuga: ${item.pressure_psi ?? "—"} psi y ${item.flow_lpm ?? "—"} L/min.`
    };
    localStorage.setItem(alertStorageKey(), JSON.stringify([alert, ...savedAlerts()].slice(0, 50)));
    renderAlertHistory();
    if (currentUser?.role === "FONTANERO") showBrowserNotification(alert);
  }

  async function prepareNotifications() {
    const button = document.getElementById("aviAsadaNotifications");
    const supported = "Notification" in window && "serviceWorker" in navigator;
    button.hidden = !supported || currentUser?.role !== "FONTANERO";
    if (!supported) return;
    try {
      notificationRegistration = await navigator.serviceWorker.register("avi-sw.js?v=20261009-5", {updateViaCache:"none"});
      await notificationRegistration.update();
      const existing = await notificationRegistration.pushManager.getSubscription();
      if (existing) {
        await request("/push/subscriptions", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(existing.toJSON())});
        pushSubscribed = true;
      }
    }
    catch { notificationRegistration = null; }
    updateNotificationButton();
  }

  function updateNotificationButton() {
    const button = document.getElementById("aviAsadaNotifications");
    if (!button || !("Notification" in window)) return;
    button.textContent = pushSubscribed ? "Push activado" : Notification.permission === "granted" ? "Completar activación" : Notification.permission === "denied" ? "Avisos bloqueados" : "Activar avisos";
    button.disabled = pushSubscribed;
  }

  async function showBrowserNotification(alert) {
    if (pushSubscribed || Notification.permission !== "granted") return;
    const registration = notificationRegistration || await navigator.serviceWorker.ready.catch(() => null);
    if (!registration) return;
    await registration.showNotification(`AVI · ${alert.sector}`, {
      body:alert.message,
      tag:`avi-asada-${CURRENT_PROPERTY}-${alert.node_id}`,
      data:{url:location.href},
      icon:"favicon.ico"
    });
  }

  loginForm.addEventListener("submit", async event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(loginForm));
    const button = loginForm.querySelector("button"); button.disabled = true;
    try {
      const headers = {"Content-Type":"application/json"};
      if (setupRequired) headers["X-Setup-Key"] = String(values.setup_key || "").trim();
      const body = setupRequired ? {username:values.username,password:values.password,full_name:values.full_name,role:"ADMIN"} : {username:values.username,password:values.password};
      const user = await request(setupRequired ? "/setup" : "/login", {method:"POST",headers,body:JSON.stringify(body)});
      token = user.access_token; sessionStorage.setItem(tokenKey, token); loginForm.reset(); showSession(user); await loadContext();
    } catch (error) {
      message.textContent = setupRequired && /configuración|clave/i.test(error.message)
        ? "La clave inicial no coincide. Cópiala exactamente, sin espacios antes ni después."
        : error.message;
    }
    finally { button.disabled = false; }
  });

  document.getElementById("aviAsadaUserForm").addEventListener("submit", async event => {
    event.preventDefault(); const button = event.target.querySelector("button"); button.disabled = true;
    try { await request("/users", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(new FormData(event.target)))}); event.target.reset(); await loadUsers(); message.textContent="Usuario de AVI creado."; }
    catch(error) { message.textContent=error.message; }
    finally { button.disabled=false; }
  });
  document.getElementById("aviAsadaOrderList").addEventListener("click", async event => {
    const button = event.target.closest(".asada-order-claim");
    if (!button) return;
    button.disabled = true;
    try {
      await request(`/work-orders/${button.dataset.orderId}/claim`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expected_updated_at:button.dataset.updatedAt})});
      orderInteractionUntil = 0;
      message.textContent = "Orden tomada. Ya puedes registrar la atención.";
      await loadContext();
    } catch (error) { message.textContent = error.message; }
    finally { button.disabled = false; }
  });
  document.getElementById("aviAsadaOrderList").addEventListener("submit", async event => {
    const form = event.target.closest(".asada-order-form");
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector("button"); button.disabled = true;
    try {
      const values = Object.fromEntries(new FormData(form));
      await request(`/work-orders/${form.dataset.orderId}/updates`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...values,expected_updated_at:form.dataset.updatedAt})});
      orderInteractionUntil = 0;
      message.textContent = values.status === "RESUELTA" ? "Orden resuelta y registrada en ASADA Monitor." : "Seguimiento guardado en ASADA Monitor.";
      await loadContext();
    } catch (error) { message.textContent = error.message; }
    finally { button.disabled = false; }
  });
  for (const eventName of ["focusin", "pointerdown", "input", "change"]) {
    document.getElementById("aviAsadaOrderList").addEventListener(eventName, () => {
      orderInteractionUntil = Date.now() + 30000;
    });
  }
  document.getElementById("aviAsadaRefresh").addEventListener("click", loadContext);
  document.getElementById("aviAsadaNotifications").addEventListener("click", async () => {
    if (!("Notification" in window)) return;
    const permission = await Notification.requestPermission();
    if (permission === "granted") {
      try {
        const config = await request("/push/config");
        if (!config.enabled) throw new Error("El servidor todavía no tiene configuradas las claves push.");
        notificationRegistration ||= await navigator.serviceWorker.ready;
        let subscription = await notificationRegistration.pushManager.getSubscription();
        if (!subscription) subscription = await notificationRegistration.pushManager.subscribe({
          userVisibleOnly:true,
          applicationServerKey:urlBase64ToUint8Array(config.public_key)
        });
        await request("/push/subscriptions", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(subscription.toJSON())});
        pushSubscribed = true;
        message.textContent = "Notificaciones push activadas para este celular.";
      } catch (error) {
        message.textContent = error.message;
      }
    } else {
      message.textContent = "El navegador no autorizó los avisos. Las alertas seguirán visibles dentro de AVI.";
    }
    updateNotificationButton();
  });

  function urlBase64ToUint8Array(value) {
    const padding = "=".repeat((4 - value.length % 4) % 4);
    const base64 = (value + padding).replace(/-/g, "+").replace(/_/g, "/");
    return Uint8Array.from(atob(base64), character => character.charCodeAt(0));
  }
  logoutButton.addEventListener("click", () => logout("Sesión de AVI cerrada."));
  request("/status").then(state => state.user ? (showSession(state.user), loadContext()) : showLogin(state.setup_required)).catch(error => showLogin(false, error.message));
})();
