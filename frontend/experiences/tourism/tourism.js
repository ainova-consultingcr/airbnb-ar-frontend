/* AVI Tourism experience: tourist places and nearby businesses. */
"use strict";

function showTouristPlaces(places) {
  clearCTAs();
  const actionArea = document.getElementById("actionArea");
  if (!actionArea || !Array.isArray(places)) return;
  setLastActionContext("tourist_places", "lugares turisticos", places[0] || {}, places);

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const list = document.createElement("div");
  list.className = "place-list tourist-place-list";
  const fragment = document.createDocumentFragment();

  places.forEach((place) => {
    const card = document.createElement("article");
    card.className = "place-card tourist-card";

    const category = document.createElement("div");
    category.className = "place-category";
    category.textContent = place.category?.[langKey] || "";

    const name = document.createElement("h3");
    name.className = "place-name";
    name.textContent = place.name || "";

    const summary = document.createElement("p");
    summary.className = "place-summary";
    summary.textContent = place.summary?.[langKey] || "";

    const source = document.createElement("span");
    source.className = "place-source";
    source.textContent = `${langKey === "en" ? "Source" : "Fuente"}: ${place.source || ""}`;

    const links = document.createElement("div");
    links.className = "place-links";

    if (place.info_url) {
      const infoButton = document.createElement("button");
      infoButton.className = "place-link primary";
      infoButton.textContent = langKey === "en" ? "Official info" : "Informaci\u00f3n";
      infoButton.onclick = () => openExternalUrl(place.info_url);
      links.appendChild(infoButton);
    }

    if (place.map_url) {
      const mapButton = document.createElement("button");
      mapButton.className = "place-link";
      mapButton.textContent = langKey === "en" ? "Open map" : "Ver mapa";
      mapButton.onclick = () => openExternalUrl(place.map_url);
      links.appendChild(mapButton);
    }

    if (place.booking_url) {
      const bookingButton = document.createElement("button");
      bookingButton.className = "place-link";
      bookingButton.textContent = langKey === "en" ? "Book entry" : "Reservar";
      bookingButton.onclick = () => openExternalUrl(place.booking_url);
      links.appendChild(bookingButton);
    }

    card.append(category, name, summary, source, links);
    fragment.appendChild(card);
  });

  list.appendChild(fragment);
  actionArea.appendChild(list);
}
function showNearbyBusinesses(businesses) {
  clearCTAs();
  const actionArea = document.getElementById("actionArea");
  if (!actionArea || !Array.isArray(businesses)) return;
  setLastActionContext("nearby_businesses", "servicios cercanos", businesses[0] || {}, businesses);

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const list = document.createElement("div");
  list.className = "place-list business-place-list";
  const fragment = document.createDocumentFragment();

  businesses.forEach((business) => {
    const card = document.createElement("article");
    card.className = "place-card business-card";

    const category = document.createElement("div");
    category.className = "place-category";
    category.textContent = business.category?.[langKey] || "";

    const name = document.createElement("h3");
    name.className = "place-name";
    name.textContent = business.name?.[langKey] || "";

    const summary = document.createElement("p");
    summary.className = "place-summary";
    summary.textContent = business.summary?.[langKey] || "";

    const details = document.createElement("div");
    details.className = "place-summary";
    const detailLines = [
      business.recommended_by ? (langKey === "en" ? `Recommended by: ${business.recommended_by}` : `Recomendado por: ${business.recommended_by}`) : "",
      business.address ? (langKey === "en" ? `Address: ${business.address}` : `Direccion: ${business.address}`) : "",
      business.hours ? (langKey === "en" ? `Hours: ${business.hours}` : `Horario: ${business.hours}`) : "",
      business.phone ? (langKey === "en" ? `Phone: ${business.phone}` : `Telefono: ${business.phone}`) : ""
    ].filter(Boolean);
    details.innerHTML = detailLines.map((line) => `<span style="display:block">${line}</span>`).join("");

    const links = document.createElement("div");
    links.className = "place-links";

    const directionsUrl = business.directions_url || business.map_url;
    if (directionsUrl) {
      const mapButton = document.createElement("button");
      mapButton.className = "place-link primary";
      mapButton.textContent = langKey === "en" ? "Direct route" : "Ruta directa";
      mapButton.onclick = () => openExternalUrl(directionsUrl);
      links.appendChild(mapButton);
    }

    if (business.info_url) {
      const infoButton = document.createElement("button");
      infoButton.className = "place-link";
      infoButton.textContent = langKey === "en" ? "Official site" : "Sitio oficial";
      infoButton.onclick = () => openExternalUrl(business.info_url);
      links.appendChild(infoButton);
    }

    card.append(category, name, summary);
    if (detailLines.length) card.appendChild(details);
    card.appendChild(links);
    fragment.appendChild(card);
  });

  list.appendChild(fragment);
  actionArea.appendChild(list);
}
