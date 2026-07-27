// AVI shared interface, branding, speech and action rendering.
let hideTimer = null;
let audioUnlocked = false;

   function unlockAudio() {
    if (audioUnlocked) return;
    speechSynthesis.getVoices();
    const silent = new SpeechSynthesisUtterance("");
    silent.volume = 0;
    window.speechSynthesis.speak(silent);

  audioUnlocked = true;
}
  function applyBranding(playAudio = false) {

  const btn = document.getElementById("sendBtn");
  const propertyName = document.getElementById("propertyName");
  const assistantStatus = document.getElementById("assistantStatus");

  if (!PROPERTY_CONFIG) return;

 const theme = PROPERTY_CONFIG.theme || UI_THEME;
  document.body.classList.toggle("auto-parts-bg", PROPERTY_CONFIG.type === "auto_parts_store");

  if (btn) {
    btn.style.background = theme.button;
    btn.style.color = theme.buttonText;
  }
  document.documentElement.style.setProperty("--avi-accent", theme.button || "#86c45c");
  document.documentElement.style.setProperty(
    "--avi-accent-text",
    theme.buttonText || "#15240d"
  );
  document.documentElement.style.setProperty("--avi-panel", theme.panel || "rgba(15, 23, 42, 0.84)");

  const config = PROPERTY_CONFIG;
  if (!config) return;

  if (propertyName) propertyName.textContent = config.name;
  if (assistantStatus) {
    assistantStatus.textContent = CURRENT_LANG.startsWith("en")
      ? "Digital concierge available"
      : "Asistente digital disponible";
  }


  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  showARAnswer(config.welcome[langKey], playAudio);
  if (typeof setupGuidedPartsSearch === "function") setupGuidedPartsSearch();
  if (typeof setupGuidedHardwareSearch === "function") setupGuidedHardwareSearch();
  if (typeof setupGuidedWellnessSearch === "function") setupGuidedWellnessSearch();
}




function pickBestVoice(targetLang) {

  const voices = speechSynthesis.getVoices();
  if (!voices || voices.length === 0) return null;

  const langPrefix = targetLang.split("-")[0]; // es / en

  // palabras comunes en voces femeninas
  const femaleHints = [
    "female",
    "woman",
    "zira",
    "sabina",
    "helena",
    "sofia",
    "paulina",
    "lucia",
    "maria"
  ];

  // Priorizar una voz femenina del idioma.
  let voice = voices.find(v =>
    v.lang.toLowerCase().startsWith(langPrefix) &&
    femaleHints.some(h => v.name.toLowerCase().includes(h))
  );

  if (voice) return voice;

  // Alternativa: cualquier voz del idioma.
  voice = voices.find(v =>
    v.lang.toLowerCase().startsWith(langPrefix)
  );

  if (voice) return voice;

  // Alternativa final: la primera voz disponible.
  return voices[0] || null;
}



function hideSuggestions() {
  const container = document.getElementById("suggestions");
  if (container) {
    container.style.display = "none";
  }
}

function showSuggestions() {
  const container = document.getElementById("suggestions");

  if (container && BACKEND_SUGGESTIONS) {
    renderSuggestionsFromBackend();
    container.style.display = "flex";
  }
}



function normalizeLang(lang) {
  if (!lang) return "es-ES";
  lang = lang.toLowerCase();

  if (lang.startsWith("es")) return "es-ES";
  if (lang.startsWith("en")) return "en-US";

  // fallback
  return "es-ES";
}


function speak(text) {
  if (!text) return;

  // Cancelar lo anterior
  speechSynthesis.cancel();

  // Usar el idioma detectado en CURRENT_LANG.
  const targetLang = normalizeLang(CURRENT_LANG);
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = targetLang;

  const voice = pickBestVoice(targetLang);
  if (voice) utterance.voice = voice;

  utterance.rate = 0.95;
  utterance.pitch = 1;
  utterance.volume = 1;

  // Cerrar el panel cuando termine el audio.
  utterance.onend = () => {
    closePanel(3000);
  };

  speechSynthesis.speak(utterance);
}

function closePanel(delay = 0) {
 if (hideTimer) clearTimeout(hideTimer);

  hideTimer = setTimeout(() => {
    showSuggestions();

  }, delay);
}

function showARAnswer(text, speakAudio = true) {
  const responseCard = document.getElementById("responseCard");
  const responseText = document.getElementById("responseText");
  const responseLoading = document.getElementById("responseLoading");
  const responseLabel = document.getElementById("responseLabel");

  if (!responseCard || !responseText) return;

  const finalText = String(text || "").normalize("NFC");
  responseText.textContent = finalText;
  responseText.scrollTop = 0;
  responseLoading?.classList.remove("visible");
  responseText.style.display = "block";
  responseCard.classList.add("visible");
  if (responseLabel) {
    responseLabel.textContent = CURRENT_LANG.startsWith("en")
      ? "AVI answers"
      : "AVI responde";
  }
  hideSuggestions();

  // audio
  if (speakAudio) {
    speak(text);
  }

  if (hideTimer) clearTimeout(hideTimer);

  if (!speakAudio) {
    clearCTAs();
    closePanel(6000);
  }

}
function applyInputBranding() {

  const input = document.getElementById("questionInput");
  const textButton = document.getElementById("sendBtn");
  const config = PROPERTY_CONFIG;
  const ui = config.ui || {};

  if (!input || !config) return;

  const isEN = CURRENT_LANG.startsWith("en");
  const langKey = isEN ? "en" : "es";
input.placeholder =
  ui.input_placeholder?.[langKey]?.replace("{name}", config.name) ||
  (isEN
    ? `Ask something at ${config.name}...`
    : `Pregunta algo en ${config.name}...`);
    if (textButton) {
  textButton.textContent =
    ui.send_button?.[langKey] || (isEN ? "Send" : "Enviar");
}
}
function showLoader() {
  const responseCard = document.getElementById("responseCard");
  const responseText = document.getElementById("responseText");
  const responseLoading = document.getElementById("responseLoading");
  const responseLabel = document.getElementById("responseLabel");
  const status = document.getElementById("assistantStatus");

  responseCard?.classList.add("visible");
  responseLoading?.classList.add("visible");
  if (responseText) responseText.style.display = "none";
  if (responseLabel) {
    responseLabel.textContent = CURRENT_LANG.startsWith("en")
      ? "AVI is checking"
      : "AVI est\u00e1 consultando";
  }
  if (status) {
    status.textContent = CURRENT_LANG.startsWith("en")
      ? "Preparing your answer"
      : "Preparando tu respuesta";
  }
}

function hideLoader() {
  document.getElementById("responseLoading")?.classList.remove("visible");
  const responseText = document.getElementById("responseText");
  const status = document.getElementById("assistantStatus");
  if (responseText) responseText.style.display = "block";
  if (status) {
    status.textContent = CURRENT_LANG.startsWith("en")
      ? "Digital concierge available"
      : "Asistente digital disponible";
  }
}


 function setLoading(isLoading) {
  const btn = document.getElementById("sendBtn");
  const input = document.getElementById("questionInput");

  const isEN = CURRENT_LANG.startsWith("en");

  if (btn) {
    btn.disabled = isLoading;
    btn.textContent = isLoading ? "..." : (isEN ? "Send" : "Enviar");
  }

  if (input) {
    input.disabled = isLoading;
  }
}


function renderSuggestionsFromBackend() {
  const container = document.getElementById("suggestions");
  if (!container || !BACKEND_SUGGESTIONS) return;

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const list = BACKEND_SUGGESTIONS[langKey] || [];

  container.innerHTML = "";

  list.forEach((q) => {
    const btn = document.createElement("button");
    btn.className = "suggestion-btn";
    btn.textContent = q;
    btn.onclick = () => {
      if (typeof handleWellnessShortcut === "function" && handleWellnessShortcut(q)) return;
      const input = document.getElementById("questionInput");
      if (input) input.value = q;
      askAI();
    };

    container.appendChild(btn);
  });

  appendServiceRequestHelpSuggestion(container);
}
function showThinking() {
  if (!PROPERTY_CONFIG) return;
  showLoader();
}
function clearCTAs() {
  document.getElementById("ctaBtn")?.remove();
  document.getElementById("ctaContainer")?.remove();
  const actionArea = document.getElementById("actionArea");
  if (actionArea) actionArea.innerHTML = "";
}





function showMultipleCTA(options) {
  clearCTAs();
  const actionArea = document.getElementById("actionArea");
  if (!actionArea) return;
  if (Array.isArray(options) && options.length) {
    setLastActionContext(
      options[0].type || "cta",
      localizedValue(options[0].text, "accion disponible"),
      options[0].data || options[0],
      options.map((option) => option.data || option)
    );
  }

  const container = document.createElement("div");
  container.id = "ctaContainer";

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";

  options.forEach((opt, index) => {

    const btn = document.createElement("button");

    btn.textContent = opt.text[langKey];
    btn.className = index === 0 ? "avi-action" : "avi-action secondary";

    btn.onclick = async() => {
        setLastActionContext(
          opt.type || "cta",
          localizedValue(opt.text, "accion disponible"),
          opt.data || opt,
          [opt.data || opt]
        );
        clearCTAs();

      handleCTA(opt.type, opt.data);
    };

    container.appendChild(btn);
  });

  actionArea.appendChild(container);
}
