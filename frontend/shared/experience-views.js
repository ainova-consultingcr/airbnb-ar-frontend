// Loads only the HTML and JavaScript required by the active AVI entity.
const EXPERIENCE_ASSET_VERSION = "20260727-5";
const EXPERIENCE_CONFIG = {
  auto_parts_store: {
    panel: "frontend/experiences/auto-parts/panel.html",
    scripts: [
      "frontend/experiences/auto-parts/auto-parts.js",
      "frontend/experiences/auto-parts/workshop-demo.js"
    ]
  },
  hardware_store: {
    panel: "frontend/experiences/hardware/panel.html",
    scripts: ["frontend/experiences/hardware/hardware.js"]
  },
  wellness_sales_assistant: {
    panel: "frontend/experiences/farmasi/panel.html",
    styles: [
      "frontend/experiences/farmasi/farmasi-commerce.css",
      "frontend/experiences/farmasi/farmasi-interactions.css"
    ],
    scripts: ["frontend/experiences/farmasi/farmasi.js"]
  },
  hotel: {
    scripts: ["frontend/experiences/tourism/tourism.js"]
  },
  airbnb: {
    scripts: ["frontend/experiences/tourism/tourism.js"]
  },
  lodging: {
    scripts: ["frontend/experiences/tourism/tourism.js"]
  },
  "Tourism Assistant": {
    scripts: ["frontend/experiences/tourism/tourism.js"]
  }
};

function loadExperienceScript(path) {
  return new Promise((resolve, reject) => {
    const versionedPath = `${path}?v=${EXPERIENCE_ASSET_VERSION}`;
    const existing = document.querySelector(`script[src="${versionedPath}"]`);
    if (existing) {
      if (existing.dataset.loaded === "true") resolve();
      else existing.addEventListener("load", resolve, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = versionedPath;
    script.onload = () => {
      script.dataset.loaded = "true";
      resolve();
    };
    script.onerror = () => reject(new Error(`No se pudo cargar ${path}`));
    document.body.appendChild(script);
  });
}

function loadExperienceStyle(path) {
  const versionedPath = `${path}?v=${EXPERIENCE_ASSET_VERSION}`;
  if (document.querySelector(`link[href="${versionedPath}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = versionedPath;
  document.head.appendChild(link);
}

async function loadExperiencePanel(path) {
  const host = document.getElementById("experienceViews");
  if (!host || !path) return;

  const versionedPath = `${path}?v=${EXPERIENCE_ASSET_VERSION}`;
  const response = await fetch(versionedPath);
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${path}: ${response.status}`);
  }
  host.innerHTML = await response.text();
}

async function loadExperience(entityType) {
  const config = EXPERIENCE_CONFIG[entityType] || {};

  try {
    await loadExperienceScript("frontend/experiences/hospitality/hospitality.js");
    for (const path of config.styles || []) loadExperienceStyle(path);
    await loadExperiencePanel(config.panel);

    for (const path of config.scripts || []) {
      await loadExperienceScript(path);
    }
  } catch (error) {
    console.error("Error cargando experiencia:", error);
  }
}
