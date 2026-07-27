/* AVI Hospitality experience: lodging requests, restaurants and reservation actions. */
"use strict";

function serviceRequestHelpContent() {
  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  if (langKey === "en") {
    return {
      button: "What can I request?",
      title: "How to make a request",
      intro: "Write a clear operational request so AVI can send it to the hotel team. For example: “I need an extra towel”.",
      intent: "Use phrases like: I need, I would like to request, can you bring, I am missing, it is not working, or it is damaged.",
      examplesTitle: "Examples you can use",
      close: "Got it",
      examples: ["I need an extra towel", "The hot water is not working", "I am missing toilet paper"],
      categories: [
        ["Amenities", "Towels, soap, shampoo, toilet paper, iron, hair dryer, pillows and blankets."],
        ["Bed linen", "Sheets, pillowcases and bed linen change."],
        ["Drinks", "Water, bottles, ice and other beverages."],
        ["Cleaning", "Room cleaning, trash pickup or additional cleaning."],
        ["Maintenance", "Air conditioning, hot water, television, electricity, lock, toilet, shower, leaks or damaged equipment."],
        ["Front desk", "Keys, access cards, luggage and general requests."]
      ]
    };
  }

  return {
    button: "¿Qué puedo solicitar?",
    title: "Cómo hacer una solicitud",
    intro: "Escribe una solicitud operativa clara para que AVI pueda enviarla al equipo del alojamiento. Por ejemplo: “Necesito una toalla extra”.",
    intent: "Usa frases como: necesito, quisiera pedir, pueden traer, me hace falta, no funciona o está dañado.",
    examplesTitle: "Ejemplos que puedes usar",
    close: "Entendido",
    examples: ["Necesito una toalla extra", "El agua caliente no funciona", "Me hace falta papel higiénico"],
    categories: [
      ["Amenidades", "Toallas, jabón, champú, papel higiénico, plancha, secadora, almohadas y cobijas."],
      ["Ropa de cama", "Sábanas, fundas y cambio de ropa de cama."],
      ["Bebidas", "Agua, botellas, hielo y otras bebidas."],
      ["Limpieza", "Aseo de la habitación, basura o limpieza adicional."],
      ["Mantenimiento", "Aire acondicionado, agua caliente, televisión, electricidad, cerradura, inodoro, ducha, fugas o equipos dañados."],
      ["Recepción", "Llaves, tarjetas de acceso, equipaje y solicitudes generales."]
    ]
  };
}

function shouldShowServiceRequestHelp() {
  const urlParams = new URLSearchParams(window.location.search);
  const roomFromUrl = urlParams.get("habitacion") || urlParams.get("room") || urlParams.get("room_id");
  const room = (typeof CURRENT_ROOM !== "undefined" && CURRENT_ROOM) || roomFromUrl;
  const entity = String((typeof CURRENT_PROPERTY !== "undefined" && CURRENT_PROPERTY) || "").toLowerCase();
  const type = String(PROPERTY_CONFIG?.type || PROPERTY_CONFIG?.entity_type || PROPERTY_CONFIG?.category || "").toLowerCase();
  const serviceRequestsEnabled = PROPERTY_CONFIG?.service_requests?.enabled === true;

  return Boolean(room || serviceRequestsEnabled || entity.includes("hotel") || entity.includes("airbnb") || type.includes("hotel") || type.includes("airbnb"));
}

function appendServiceRequestHelpSuggestion(container) {
  if (!container || !shouldShowServiceRequestHelp()) return;

  const content = serviceRequestHelpContent();
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "suggestion-btn service-help-suggestion";
  btn.textContent = content.button;
  btn.onclick = showServiceRequestHelp;
  container.insertBefore(btn, container.firstChild);
}

function fillServiceRequestExample(text) {
  const input = document.getElementById("questionInput");
  if (!input) return;
  input.value = text;
  input.focus();
}

function showServiceRequestHelp() {
  clearCTAs();
  hideSuggestions();

  const actionArea = document.getElementById("actionArea");
  if (!actionArea) return;

  const content = serviceRequestHelpContent();
  const card = document.createElement("section");
  card.className = "service-request-help";
  card.setAttribute("aria-label", content.title);

  const title = document.createElement("h3");
  title.textContent = content.title;

  const intro = document.createElement("p");
  intro.textContent = content.intro;

  const grid = document.createElement("div");
  grid.className = "service-request-help-grid";

  content.categories.forEach(([name, description]) => {
    const row = document.createElement("div");
    row.className = "service-request-help-row";

    const strong = document.createElement("strong");
    strong.textContent = name;

    const span = document.createElement("span");
    span.textContent = description;

    row.append(strong, span);
    grid.appendChild(row);
  });

  const intent = document.createElement("p");
  intent.textContent = content.intent;

  const examplesTitle = document.createElement("p");
  examplesTitle.textContent = content.examplesTitle;

  const examples = document.createElement("div");
  examples.className = "service-request-example-list";
  content.examples.forEach((example) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "service-request-example";
    btn.textContent = example;
    btn.onclick = () => fillServiceRequestExample(example);
    examples.appendChild(btn);
  });

  const actions = document.createElement("div");
  actions.className = "service-request-help-actions";
  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.className = "avi-action secondary";
  closeBtn.textContent = content.close;
  closeBtn.onclick = () => {
    clearCTAs();
    showSuggestions();
  };
  actions.appendChild(closeBtn);

  card.append(title, intro, grid, intent, examplesTitle, examples, actions);
  actionArea.appendChild(card);
}
function showCTA(cta) {
  clearCTAs();
  const actionArea = document.getElementById("actionArea");
  if (!actionArea) return;
  setLastActionContext(cta.type || "cta", localizedValue(cta.text, "accion"), cta);

  const btn = document.createElement("button");
  btn.id = "ctaBtn";
  btn.className = "avi-action";

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";

  btn.textContent = cta.text[langKey];

  btn.onclick = () => {
    btn.style.display = "none";
    setTimeout(() => {
      window.open(cta.url, "_blank");
    }, 100);
  };

  actionArea.appendChild(btn);
}
function reserveRestaurant(restaurant) {
  if (!restaurant?.whatsapp) return;

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const message = langKey === "en"
    ? `Hello, I would like to book a table at ${restaurant.name}. AVI code: ${restaurant.lead_id || "N/A"}`
    : `Hola, quiero reservar una mesa en ${restaurant.name}. Código AVI: ${restaurant.lead_id || "N/A"}`;

  trackLeadEvent(
    "reservation_started",
    "restaurant",
    restaurant.name,
    restaurant.lead_id
  );

  const phone = String(restaurant.whatsapp).replace(/\D/g, "");
  openExternalUrl(`https://wa.me/${phone}?text=${encodeURIComponent(message)}`);
}

function showRestaurants(restaurants) {
  clearCTAs();
  const actionArea = document.getElementById("actionArea");
  if (!actionArea || !Array.isArray(restaurants)) return;
  setLastActionContext("restaurants", "restaurantes", restaurants[0] || {}, restaurants);

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const list = document.createElement("div");
  list.className = "place-list";
  const fragment = document.createDocumentFragment();

  restaurants.forEach((restaurant) => {
    const card = document.createElement("article");
    card.className = "place-card restaurant-card";

    const category = document.createElement("div");
    category.className = "place-category";
    category.textContent = restaurant.category?.[langKey] || (
      langKey === "en" ? "Recommended restaurant" : "Restaurante recomendado"
    );

    const name = document.createElement("h3");
    name.className = "place-name";
    name.textContent = restaurant.name || "";

    const summary = document.createElement("p");
    summary.className = "place-summary";
    summary.textContent = restaurant.summary?.[langKey] || "";

    const links = document.createElement("div");
    links.className = "place-links";

    if (restaurant.whatsapp) {
      const reserveButton = document.createElement("button");
      reserveButton.className = "place-link primary";
      reserveButton.textContent = langKey === "en" ? "Book table" : "Reservar";
      reserveButton.onclick = () => reserveRestaurant(restaurant);
      links.appendChild(reserveButton);
    }

    const isHotelRestaurant = restaurant.has_own_restaurant || restaurant.type === "own_restaurant";
    const directionsUrl = isHotelRestaurant ? null : (restaurant.directions_url || restaurant.map_url);
    if (directionsUrl) {
      const mapButton = document.createElement("button");
      mapButton.className = "place-link";
      mapButton.textContent = langKey === "en" ? "Direct route" : "Ruta directa";
      mapButton.onclick = () => openExternalUrl(directionsUrl);
      links.appendChild(mapButton);
    }

    if (restaurant.menu_url) {
      const menuButton = document.createElement("button");
      menuButton.className = "place-link";
      menuButton.textContent = langKey === "en" ? "View menu" : "Ver menú";
      menuButton.onclick = () => openExternalUrl(restaurant.menu_url);
      links.appendChild(menuButton);
    }

    card.append(category, name, summary, links);
    fragment.appendChild(card);
  });

  list.appendChild(fragment);
  actionArea.appendChild(list);
}
function handleCTA(type, data) {
  if (type === "transport") {
    const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
    const serviceName = data?.name || (langKey === "en" ? "airport transportation" : "transporte al aeropuerto");
    const priceText = data?.price ? ` ${langKey === "en" ? "Approximate price" : "Precio aproximado"}: $${data.price}.` : "";
    const message = data?.message?.[langKey] || (
      langKey === "en"
        ? `Hello, I would like to book ${serviceName}.${priceText}`
        : `Hola, quiero reservar ${serviceName}.${priceText}`
    );
    openWhatsApp(data?.whatsapp, message);
  }

  if (type === "external_restaurants") {
    document.getElementById("questionInput").value =
        "otros restaurantes";

    askAI();
  }

  if (type === "own_restaurant") {

      window.open(
      `https://wa.me/${data.whatsapp}?text=${encodeURIComponent(
        "Hola, quiero reservar una mesa en el restaurante."
      )}`
    );

}
if (type === "restaurant") {

  window.open(`https://wa.me/${data.whatsapp}?text=${encodeURIComponent("quiero reservar")}`);


    return;
}

  if (type === "tour") {
    window.open(`https://wa.me/${data.whatsapp}?text=${encodeURIComponent("quiero reservar")}`);
  }
}
