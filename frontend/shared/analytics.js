(function () {
  "use strict";

  const apiBase = window.API_BASE_URL || (location.hostname === "localhost" ? "http://localhost:8000" : "https://airbnb-ar-assistant.onrender.com");
  const params = new URLSearchParams(location.search);
  const propertyId = window.CURRENT_PROPERTY || params.get("entity") || params.get("property") || "hotel_demo";
  const sessionKey = "avi_analytics_session";
  const sessionId = sessionStorage.getItem(sessionKey) || (crypto.randomUUID ? crypto.randomUUID() : `avi-${Date.now()}-${Math.random().toString(16).slice(2)}`);
  sessionStorage.setItem(sessionKey, sessionId);
  const seen = new Set();
  let clickContext = null;

  function traffic() {
    let referrer = "";
    try { referrer = document.referrer ? new URL(document.referrer).hostname : ""; } catch (_) {}
    return {
      session_id: sessionId,
      source: params.get("utm_source") || params.get("source") || referrer || "directo",
      medium: params.get("utm_medium") || (referrer ? "referido" : "directo"),
      campaign: params.get("utm_campaign") || "",
      referrer,
      landing_page: `${location.pathname}${location.search}`,
      language: (navigator.language || "es").slice(0, 2)
    };
  }

  function send(eventType, category, itemName, metadata) {
    const body = JSON.stringify({
      property_id: propertyId,
      event_type: eventType,
      category: category || "general",
      item_name: itemName || "",
      lead_id: null,
      metadata: Object.assign(traffic(), metadata || {})
    });
    fetch(`${apiBase}/track-lead`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true
    }).catch(() => {});
  }

  function cardContext(element) {
    const card = element && element.closest ? element.closest(".place-card") : null;
    if (!card) return { category: "alojamiento", item: propertyId };
    return {
      category: (card.querySelector(".place-category")?.textContent || "proveedor").trim(),
      item: (card.querySelector(".place-name")?.textContent || propertyId).trim()
    };
  }

  function scanImpressions(root) {
    const cards = root.querySelectorAll ? root.querySelectorAll(".place-card") : [];
    cards.forEach((card) => {
      const context = cardContext(card);
      const key = `${context.category}:${context.item}`;
      if (!context.item || seen.has(key)) return;
      seen.add(key);
      send("provider_impression", context.category, context.item);
    });
  }

  const nativeOpen = window.open.bind(window);
  window.open = function (url) {
    if (/https:\/\/(wa\.me|api\.whatsapp\.com)/i.test(String(url || ""))) {
      const context = clickContext || { category: "alojamiento", item: propertyId };
      send("whatsapp_click", context.category, context.item, { destination: "whatsapp" });
    }
    return nativeOpen.apply(window, arguments);
  };

  document.addEventListener("click", (event) => {
    const button = event.target.closest("button, a");
    if (!button) return;
    const context = cardContext(button);
    clickContext = context;
    setTimeout(() => { clickContext = null; }, 500);

    const label = (button.textContent || "").trim().toLowerCase();
    if (button.id === "sendBtn" || button.classList.contains("suggestion-btn")) {
      const question = button.classList.contains("suggestion-btn") ? label : (document.getElementById("questionInput")?.value || "").trim();
      if (question) send("search", "consulta", question);
      return;
    }
    if (/informaci|sitio|menú|menu|mapa|ruta|official|directions|book entry/.test(label)) {
      send("info_click", context.category, context.item, { action_label: label });
    }
  }, true);

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.target?.id !== "questionInput") return;
    const question = String(event.target.value || "").trim();
    if (question) send("search", "consulta", question);
  }, true);

  document.addEventListener("DOMContentLoaded", () => {
    send("property_view", "alojamiento", propertyId);
    scanImpressions(document);
    new MutationObserver((mutations) => mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => {
      if (node.nodeType === 1) {
        if (node.matches?.(".place-card")) scanImpressions(node.parentElement || document);
        else scanImpressions(node);
      }
    }))).observe(document.body, { childList: true, subtree: true });
  });
})();
