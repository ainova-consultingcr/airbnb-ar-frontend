// AVI shared runtime: environment, entity and language configuration.
    const IS_LOCAL_DEVELOPMENT = ["localhost", "127.0.0.1"].includes(
      window.location.hostname
    );
    const API_BASE_URL = IS_LOCAL_DEVELOPMENT
      ? "http://localhost:8000"
      : "https://airbnb-ar-assistant.onrender.com";

    async function trackLeadEvent(eventType, category, itemName, leadId, metadata = {}) {

  try {

    await fetch(`${API_BASE_URL}/track-lead`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        property_id: CURRENT_PROPERTY,
        event_type: eventType,
        category: category,
        item_name: itemName,
        lead_id: leadId,
        metadata: metadata
      })
    });

  } catch (err) {
    console.error("TRACK ERROR:", err);
  }
}
  function getLanguageFromURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get("lang");
  }

  function getBrowserLanguage() {
    return navigator.language || navigator.userLanguage || "es-ES";
  }

  function getCurrentLanguage() {
    return getLanguageFromURL() || getBrowserLanguage();
  }

  const CURRENT_LANG = getCurrentLanguage();
  let BACKEND_SUGGESTIONS = null;
  let PROPERTY_CONFIG = null;

  async function loadPropertyConfig() {
  try {
    const res = await fetch(
      `${API_BASE_URL}/property?property_id=${encodeURIComponent(CURRENT_PROPERTY)}`
    );
    const data = await res.json();

    PROPERTY_CONFIG = data;
    BACKEND_SUGGESTIONS = data.suggestions || null;

  } catch (err) {
    console.error("Error cargando config:", err);
  }
}

  function getPropertyFromURL() {
  const params = new URLSearchParams(window.location.search);
  const entity = params.get("entity") || params.get("property");
  return entity || "hotel_demo";
}

const CURRENT_PROPERTY = getPropertyFromURL();

