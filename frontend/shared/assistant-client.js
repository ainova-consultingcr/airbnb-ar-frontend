// AVI assistant API request and response orchestration.
let responseRenderToken = 0;

async function askAI() {
  const input = document.getElementById("questionInput");
  if (!input || !input.value.trim()) return;

  showThinking();
  unlockAudio();
  clearCTAs();
  hideSuggestions();
  const question = input.value.trim();
  const negativeReply = isNegativeReply(question);
  const requestContext = { ...getConversationContextForQuestion(question) };
  if (negativeReply && requestContext.type) {
    requestContext.decline_count = activeConversationContext?.decline_count || 0;
    activeConversationContext = {
      ...activeConversationContext,
      decline_count: (activeConversationContext?.decline_count || 0) + 1
    };
  }
  if (
    !isContinuationReply(question)
    && !negativeReply
    && !["auto_parts_search", "hardware_search", "wellness_profile"].includes(activeConversationContext?.type)
  ) {
    activeConversationContext = null;
  }
  const requestCard = document.getElementById("serviceRequestCard");
  if (requestCard) requestCard.style.display = "none";
  const currentRenderToken = ++responseRenderToken;

  try {
    setLoading(true);

    showLoader();

    const res = await fetch(
     `${API_BASE_URL}/ask`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          property_id: CURRENT_PROPERTY,
          question: question,
          language: CURRENT_LANG.startsWith("en") ? "en" : "es",
          conversation_context: requestContext,
          room_id: CURRENT_ROOM || null,
          guest_session_id: GUEST_SESSION_ID
        })
      }
    );
    if (!res.ok) {
      let detail = "";
       hideLoader();
      try {
        const err = await res.json();
        detail = err?.detail ? ` (${err.detail})` : "";
      } catch (e) {}

      const errors = PROPERTY_CONFIG?.ui?.errors || {};
      const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";

  const baseServerError = errors.server?.[langKey] || "Server error";
  showARAnswer(
  IS_LOCAL_DEVELOPMENT && detail ? `${baseServerError}${detail}` : baseServerError,
  false
);
      return;
    }
    const data = await res.json();
    if (data.service_request) {
      startServiceRequestPolling(data.service_request);
    }
    if (data.reset_context) {
      activeConversationContext = null;
    }
    setContextFromResponseData(data, question);
    if (requestContext?.type === "wellness_profile" && !data.reset_context) {
      activeConversationContext = requestContext;
    }


    if (data.suggestions) {

  BACKEND_SUGGESTIONS = data.suggestions;
  renderSuggestionsFromBackend();
}

if (data.cta_options) {
  setTimeout(() => {
    if (currentRenderToken !== responseRenderToken) return;
    showMultipleCTA(data.cta_options);
  }, 300);
}
if (data.place_options) {
  setTimeout(() => {
    if (currentRenderToken !== responseRenderToken) return;
    if (typeof showTouristPlaces === "function") showTouristPlaces(data.place_options);
  }, 300);
}
if (data.restaurant_options) {
  setTimeout(() => {
    if (currentRenderToken !== responseRenderToken) return;
    showRestaurants(data.restaurant_options);
  }, 300);
}
if (data.business_options) {
  setTimeout(() => {
    if (currentRenderToken !== responseRenderToken) return;
    if (typeof showNearbyBusinesses === "function") showNearbyBusinesses(data.business_options);
  }, 300);
}
   const answer = data?.answer;

hideLoader();
if (!answer) {
  showARAnswer(
    CURRENT_LANG.startsWith("en")
      ? "I could not prepare an answer. Please try again."
      : "No pude preparar una respuesta. Intenta nuevamente.",
    false
  );
  return;
}
if (data.service_request) {
  input.value = "";
  return;
}
showARAnswer(answer, true);
if (data.cta) {
  setTimeout(() => {
    showCTA(data.cta);
  }, 600); // pequeno delay para evitar que el render lo tape
}

input.value = "";


  } catch (err) {
    console.error("Fetch error:", err);
    hideLoader();

    const ui = PROPERTY_CONFIG.ui || {};
    const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";

  showARAnswer(
  ui.errors?.network?.[langKey] ||
  "Error de red. Revisa tu conexion.",
  false
);


  } finally {
    setLoading(false);
  }

}

