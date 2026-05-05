let hideTimer = null;

/* =========================
   MOSTRAR / OCULTAR PANEL
   ========================= */
function showARAnswer(text, speakAudio = true) {
  const float = document.getElementById("arFloat");
  const panel = document.getElementById("arPanel");
  const arText = document.getElementById("arText");

  if (!float || !panel || !arText) return;

  // Reset seguro
  panel.setAttribute("scale", "0.7 0.7 0.7");
  float.setAttribute("visible", "true");

  // Texto (forzar render)
  arText.setAttribute("value", " ");
  setTimeout(() => {
    arText.setAttribute("value", text);
  }, 40);

  // Animación de entrada
  panel.setAttribute("animation__in", {
    property: "scale",
    from: "0.7 0.7 0.7",
    to: "1 1 1",
    dur: 350,
    easing: "easeOutBack"
  });

  // Voz
  if (speakAudio) {
    const lang = detectLanguage(text);
    speak(text, lang);
  }

  // Auto-ocultar
  if (hideTimer) clearTimeout(hideTimer);
  hideTimer = setTimeout(() => {
    panel.setAttribute("animation__out", {
      property: "scale",
      from: "1 1 1",
      to: "0.7 0.7 0.7",
      dur: 300,
      easing: "easeInQuad"
    });

    setTimeout(() => {
      float.setAttribute("visible", "false");
    }, 320);

  }, 8000);
}


/* =========================
   CONSULTAR IA
   ========================= */
async function askAI() {
  const res = await fetch(
    //"https://airbnb-ar-assistant.onrender.com/ask",
    "https://gayla-subcalibre-destiny.ngrok-free.dev/ask",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_id: "demo_property",
        question: "¿Cómo uso el aire acondicionado?"
      })
    }
  );

  const data = await res.json();

  // 🔥 AQUÍ sí se llama
  showARAnswer(data.answer);
}
