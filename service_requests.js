function getRoomFromURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get("habitacion") || params.get("room") || params.get("unidad") || "";
}
const CURRENT_ROOM = getRoomFromURL();
const AVI_SESSION_KEY = "avi_guest_session_" + CURRENT_PROPERTY + "_" + (CURRENT_ROOM || "no_room");
let GUEST_SESSION_ID = localStorage.getItem(AVI_SESSION_KEY);
if (!GUEST_SESSION_ID) {
  GUEST_SESSION_ID = crypto.randomUUID ? crypto.randomUUID() : "AVI-" + Date.now();
  localStorage.setItem(AVI_SESSION_KEY, GUEST_SESSION_ID);
}
let activeServiceRequest = null;
let serviceRequestPollTimer = null;
const SERVICE_REQUEST_POLL_INTERVAL_MS = 30000;
const activeRequestKey = () => "avi_active_request_" + CURRENT_PROPERTY + "_" + CURRENT_ROOM;

function ensureServiceRequestCard() {
  if (document.getElementById("serviceRequestCard")) return;
  const card = document.createElement("section");
  card.id = "serviceRequestCard";
  card.style.cssText = "position:fixed;top:82px;left:50%;z-index:99998;width:min(520px,calc(100vw - 32px));padding:14px 16px;transform:translateX(-50%);border:1px solid rgba(255,255,255,.18);border-radius:18px;color:#fff;background:rgba(8,20,32,.94);box-shadow:0 18px 42px rgba(0,0,0,.34);display:none";
  card.innerHTML = '<div style="display:flex;justify-content:space-between;gap:12px"><strong id="serviceRequestTitle">Solicitud AVI</strong><span id="serviceRequestStatus"></span></div><p id="serviceRequestDescription" style="margin:8px 0;color:rgba(255,255,255,.78)"></p><div id="serviceRequestActions" style="display:flex;gap:8px"></div>';
  document.body.appendChild(card);
}
function renderServiceRequest(request) {
  if (!request) return;
  ensureServiceRequestCard();
  activeServiceRequest = request;
  const responseCard = document.getElementById("responseCard");
  if (responseCard) responseCard.classList.remove("visible");
  localStorage.setItem(activeRequestKey(), request.id);
  document.getElementById("serviceRequestTitle").textContent = "Habitación " + CURRENT_ROOM + " · " + request.id;
  document.getElementById("serviceRequestDescription").textContent = request.description || "";
  document.getElementById("serviceRequestStatus").textContent = request.status || "Pendiente";
  const actions = document.getElementById("serviceRequestActions");
  actions.innerHTML = "";
  if (request.status === "Entregada" && request.guest_confirmation !== "Confirmada") {
    [["Sí, la recibí", true, "#86c45c"], ["Aún no", false, "#f97373"]].forEach((item) => {
      const button = document.createElement("button");
      button.textContent = CURRENT_LANG.startsWith("en") ? (item[1] ? "Yes, received" : "Not received") : item[0];
      button.style.cssText = "flex:1;padding:10px;border:0;border-radius:11px;font-weight:800;background:" + item[2];
      button.onclick = () => confirmGuestReceipt(item[1]);
      actions.appendChild(button);
    });
  }
  if (request.status === "Cancelada") {
    const acknowledgeButton = document.createElement("button");
    acknowledgeButton.textContent = CURRENT_LANG.startsWith("en") ? "Understood" : "Entendido";
    acknowledgeButton.style.cssText = "flex:1;padding:10px;border:0;border-radius:11px;font-weight:800;background:#9ca3af;color:#111827";
    acknowledgeButton.onclick = dismissServiceRequest;
    actions.appendChild(acknowledgeButton);
  }
  document.getElementById("serviceRequestCard").style.display = "block";
}
function dismissServiceRequest() {
  localStorage.removeItem(activeRequestKey());
  activeServiceRequest = null;
  clearInterval(serviceRequestPollTimer);
  serviceRequestPollTimer = null;
  const card = document.getElementById("serviceRequestCard");
  if (card) card.style.display = "none";
  if (typeof showSuggestions === "function") showSuggestions();
  if (typeof showARAnswer === "function") {
    const fallbackWelcome = CURRENT_LANG.startsWith("en") ? "How else can I help you?" : "¿En qué más puedo ayudarte?";
    const welcomeMessage = typeof localizedValue === "function" ? localizedValue(PROPERTY_CONFIG?.welcome, fallbackWelcome) : fallbackWelcome;
    showARAnswer(welcomeMessage, false);
  }
}
async function pollServiceRequest() {
  const id = activeServiceRequest?.id || localStorage.getItem(activeRequestKey());
  if (!id || !CURRENT_ROOM) return;
  try {
    const query = new URLSearchParams({property_id: CURRENT_PROPERTY, guest_session_id: GUEST_SESSION_ID});
    const response = await fetch(API_BASE_URL + "/service-requests/" + encodeURIComponent(id) + "?" + query);
    if (!response.ok) return;
    const prior = activeServiceRequest?.status;
    const request = await response.json();
    const currentId = activeServiceRequest?.id || localStorage.getItem(activeRequestKey());
    if (String(currentId || "") !== String(id)) return;
    const card = document.getElementById("serviceRequestCard");
    if (!activeServiceRequest || request.status !== prior || card?.style.display !== "none") {
      renderServiceRequest(request);
    } else {
      activeServiceRequest = request;
    }
  } catch (error) { console.warn("REQUEST POLL ERROR", error); }
}
function startServiceRequestPolling(request) {
  renderServiceRequest(request);
  clearInterval(serviceRequestPollTimer);
  serviceRequestPollTimer = setInterval(pollServiceRequest, SERVICE_REQUEST_POLL_INTERVAL_MS);
}
async function confirmGuestReceipt(received) {
  if (!activeServiceRequest) return;
  const response = await fetch(API_BASE_URL + "/service-requests/" + encodeURIComponent(activeServiceRequest.id) + "/confirm", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({property_id: CURRENT_PROPERTY, guest_session_id: GUEST_SESSION_ID, received})
  });
  if (!response.ok) return;
  const updatedRequest = await response.json();
  if (received) {
    dismissServiceRequest();
  } else {
    renderServiceRequest(updatedRequest);
  }
}
function restoreServiceRequest() {
  ensureServiceRequestCard();
  clearInterval(serviceRequestPollTimer);
  serviceRequestPollTimer = null;
  if (CURRENT_ROOM && localStorage.getItem(activeRequestKey())) {
    pollServiceRequest();
    serviceRequestPollTimer = setInterval(pollServiceRequest, SERVICE_REQUEST_POLL_INTERVAL_MS);
  }
}