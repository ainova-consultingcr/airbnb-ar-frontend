// AVI shared conversation state and continuation handling.
let activeConversationContext = null;

function localizedValue(value, fallback = "") {
  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value[langKey] || value.es || value.en || fallback;
  }
  return value || fallback;
}

function setLastActionContext(actionType, topic, item = {}, options = []) {
  activeConversationContext = {
    type: "last_action",
    action_type: actionType,
    topic,
    item,
    options: Array.isArray(options) ? options.slice(0, 5) : []
  };
}

function isContinuationReply(text) {
  const normalized = (text || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  return [
    "si",
    "si quiero",
    "si algo mas",
    "algo mas",
    "mas",
    "mas informacion",
    "otra opcion",
    "otra cosa",
    "ok",
    "okay",
    "dale",
    "claro",
    "correcto",
    "quiero",
    "quiero ayuda",
    "ayuda",
    "ayudame",
    "me interesa",
    "reservar",
    "reserva",
    "quiero reservar",
    "yes",
    "yes please",
    "more",
    "more info",
    "something else",
    "yeah",
    "yep",
    "sure",
    "help me"
  ].includes(normalized);
}

function isNegativeReply(text) {
  const normalized = (text || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  return [
    "no",
    "no gracias",
    "gracias no",
    "por ahora no",
    "ahora no",
    "no thanks",
    "not now"
  ].includes(normalized);
}

function getConversationContextForQuestion(question) {
  if (!activeConversationContext) return {};
  if (activeConversationContext.type === "auto_parts_search") {
    if (isContinuationReply(question) || isNegativeReply(question)) return activeConversationContext;
    const normalizedQuestion = (question || "").toLowerCase();
    const vehicle = activeConversationContext.vehicle || {};
    const part = activeConversationContext.part || {};
    const signals = [
      vehicle.make,
      vehicle.model,
      vehicle.year,
      part.name,
      part.category,
      part.sku
    ].filter(Boolean).map((value) => String(value).toLowerCase());
    return signals.some((signal) => normalizedQuestion.includes(signal))
      ? activeConversationContext
      : {};
  }
  if (activeConversationContext.type === "hardware_search") {
    if (isContinuationReply(question) || isNegativeReply(question)) return activeConversationContext;
    const normalizedQuestion = (question || "").toLowerCase();
    const item = activeConversationContext.item || {};
    const signals = [
      item.name,
      item.category,
      item.sku,
      item.aisle,
      activeConversationContext.topic
    ].filter(Boolean).map((value) => String(value).toLowerCase());
    return signals.some((signal) => normalizedQuestion.includes(signal))
      ? activeConversationContext
      : {};
  }
  if (activeConversationContext.type === "wellness_profile") {
    if (isContinuationReply(question) || isNegativeReply(question)) return activeConversationContext;
    const normalizedQuestion = (question || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
    const profile = activeConversationContext.profile || {};
    const signals = [
      profile.goal,
      profile.activity_level,
      profile.diet_style,
      profile.budget,
      ...(activeConversationContext.options || []).map((item) => item.name)
    ].filter(Boolean).map((value) => String(value).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
    return signals.some((signal) => normalizedQuestion.includes(signal))
      ? activeConversationContext
      : {};
  }
  return (isContinuationReply(question) || isNegativeReply(question)) ? activeConversationContext : {};
}

function setContextFromResponseData(data, originalQuestion = "") {
  if (data?.cta_options?.length) {
    const option = data.cta_options[0];
    setLastActionContext(
      option.type || "cta",
      localizedValue(option.text, "accion disponible"),
      option.data || option,
      data.cta_options.map((item) => item.data || item)
    );
    return;
  }
  if (data?.restaurant_options?.length) {
    setLastActionContext("restaurants", "restaurantes", data.restaurant_options[0], data.restaurant_options);
    return;
  }
  if (data?.business_options?.length) {
    setLastActionContext("nearby_businesses", "servicios cercanos", data.business_options[0], data.business_options);
    return;
  }
  if (data?.place_options?.length) {
    setLastActionContext("tourist_places", "lugares turisticos", data.place_options[0], data.place_options);
    return;
  }
  if (data?.answer && originalQuestion && !isContinuationReply(originalQuestion) && !isNegativeReply(originalQuestion)) {
    setLastActionContext(
      "general_answer",
      originalQuestion,
      {
        name: originalQuestion,
        summary: {
          es: data.answer,
          en: data.answer
        }
      },
      []
    );
  }
}

