/* AVI Auto Parts experience: extracted from the shared application shell. */
"use strict";

let selectedGuidedPart = "";

function setupGuidedPartsSearch() {
  const wrapper = document.getElementById("guidedPartsSearch");
  if (!wrapper) return;

  if (PROPERTY_CONFIG?.type !== "auto_parts_store" || !PROPERTY_CONFIG?.auto_parts) {
    wrapper.classList.remove("visible");
    return;
  }

  wrapper.classList.add("visible");

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const title = wrapper.querySelector(".guided-title");
  const makeSelect = document.getElementById("vehicleMakeSelect");
  const modelSelect = document.getElementById("vehicleModelSelect");
  const yearSelect = document.getElementById("vehicleYearSelect");
  const categorySelect = document.getElementById("partCategorySelect");
  const searchBtn = document.getElementById("guidedSearchBtn");

  title.textContent = langKey === "en"
    ? "Find your part step by step"
    : "Busca tu repuesto paso a paso";
  searchBtn.textContent = langKey === "en" ? "Ask AVI" : "Consultar con AVI";

  fillSelect(makeSelect, [
    {
      value: "",
      label: langKey === "en" ? "Make" : "Marca"
    },
    ...PROPERTY_CONFIG.auto_parts.supported_vehicles.map((vehicle) => ({
      value: vehicle.make,
      label: vehicle.make
    }))
  ]);

  fillSelect(modelSelect, [{ value: "", label: langKey === "en" ? "Model" : "Modelo" }]);
  fillSelect(yearSelect, [{ value: "", label: langKey === "en" ? "Year" : "Año" }]);
  fillPartCategories();
  renderGuidedPartChips();
  updateGuidedSearchButton();

  makeSelect.onchange = () => {
    selectedGuidedPart = "";
    updateVehicleModels();
    fillSelect(yearSelect, [{ value: "", label: langKey === "en" ? "Year" : "Año" }]);
    renderGuidedPartChips();
    updateGuidedSearchButton();
  };

  modelSelect.onchange = () => {
    selectedGuidedPart = "";
    updateVehicleYears();
    renderGuidedPartChips();
    updateGuidedSearchButton();
  };

  yearSelect.onchange = () => {
    selectedGuidedPart = "";
    renderGuidedPartChips();
    updateGuidedSearchButton();
  };

  categorySelect.onchange = () => {
    selectedGuidedPart = "";
    renderGuidedPartChips();
    updateGuidedSearchButton();
  };

  searchBtn.onclick = submitGuidedPartsSearch;
}

function updateVehicleModels() {
  const make = document.getElementById("vehicleMakeSelect")?.value;
  const modelSelect = document.getElementById("vehicleModelSelect");
  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const vehicle = PROPERTY_CONFIG.auto_parts.supported_vehicles.find((item) => item.make === make);
  const models = vehicle?.models || [];

  fillSelect(modelSelect, [
    { value: "", label: langKey === "en" ? "Model" : "Modelo" },
    ...models.map((model) => ({ value: model.name, label: model.name }))
  ]);
}

function updateVehicleYears() {
  const make = document.getElementById("vehicleMakeSelect")?.value;
  const model = document.getElementById("vehicleModelSelect")?.value;
  const yearSelect = document.getElementById("vehicleYearSelect");
  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const vehicle = PROPERTY_CONFIG.auto_parts.supported_vehicles.find((item) => item.make === make);
  const modelData = vehicle?.models.find((item) => item.name === model);
  const years = [];

  if (modelData?.years) {
    for (let year = modelData.years.to; year >= modelData.years.from; year--) {
      years.push({ value: String(year), label: String(year) });
    }
  }

  fillSelect(yearSelect, [
    { value: "", label: langKey === "en" ? "Year" : "Año" },
    ...years
  ]);
}

function fillPartCategories() {
  const categorySelect = document.getElementById("partCategorySelect");
  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const categoryLabels = {
    frenos: langKey === "en" ? "Brakes" : "Frenos",
    mantenimiento: langKey === "en" ? "Maintenance" : "Mantenimiento",
    "suspensión": langKey === "en" ? "Suspension" : "Suspensión",
    electrico: langKey === "en" ? "Electrical" : "Eléctrico",
    "eléctrico": langKey === "en" ? "Electrical" : "Eléctrico",
    visibilidad: langKey === "en" ? "Visibility" : "Visibilidad"
  };
  const categories = Array.from(new Set(
    (PROPERTY_CONFIG.auto_parts.catalog || []).map((item) => item.category).filter(Boolean)
  ));

  fillSelect(categorySelect, [
    { value: "", label: langKey === "en" ? "Part category" : "Tipo de repuesto" },
    ...categories.map((category) => ({
      value: category,
      label: categoryLabels[category] || category
    }))
  ]);
}

function getCompatibleGuidedParts() {
  const make = document.getElementById("vehicleMakeSelect")?.value;
  const model = document.getElementById("vehicleModelSelect")?.value;
  const year = Number(document.getElementById("vehicleYearSelect")?.value);
  const category = document.getElementById("partCategorySelect")?.value;
  const catalog = PROPERTY_CONFIG?.auto_parts?.catalog || [];

  return catalog.filter((part) => {
    if (category && part.category !== category) return false;
    if (!make || !model || !year) return true;

    return (part.vehicle_fitment || []).some((fitment) => {
      const universal = String(fitment.make).toLowerCase() === "universal";
      const sameVehicle = fitment.make === make && fitment.model === model;
      const inYear = year >= fitment.year_from && year <= fitment.year_to;
      return (universal || sameVehicle) && inYear;
    });
  });
}

function renderGuidedPartChips() {
  const container = document.getElementById("guidedPartChips");
  if (!container) return;

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const make = document.getElementById("vehicleMakeSelect")?.value;
  const model = document.getElementById("vehicleModelSelect")?.value;
  const year = document.getElementById("vehicleYearSelect")?.value;
  const parts = getCompatibleGuidedParts();
  container.innerHTML = "";

  if (!make || !model || !year) {
    const guide = document.createElement("button");
    guide.className = "part-chip";
    guide.disabled = true;
    guide.textContent = langKey === "en"
      ? "Choose make, model and year first"
      : "Primero elige marca, modelo y año";
    container.appendChild(guide);
    return;
  }

  if (!parts.length) {
    const empty = document.createElement("button");
    empty.className = "part-chip";
    empty.disabled = true;
    empty.textContent = langKey === "en" ? "No matching catalog item" : "Sin coincidencias en catálogo";
    container.appendChild(empty);
  }

  parts.forEach((part) => {
    const chip = document.createElement("button");
    chip.className = "part-chip" + (selectedGuidedPart === part.name ? " selected" : "");
    chip.textContent = part.name;
    chip.onclick = () => {
      selectedGuidedPart = part.name;
      renderGuidedPartChips();
      updateGuidedSearchButton();
    };
    container.appendChild(chip);
  });

  const otherChip = document.createElement("button");
  otherChip.className = "part-chip" + (selectedGuidedPart === "otro repuesto" ? " selected" : "");
  otherChip.textContent = langKey === "en" ? "I need another part" : "No veo mi repuesto";
  otherChip.onclick = () => {
    selectedGuidedPart = "otro repuesto";
    renderGuidedPartChips();
    updateGuidedSearchButton();
  };
  container.appendChild(otherChip);
}

function updateGuidedSearchButton() {
  const searchBtn = document.getElementById("guidedSearchBtn");
  if (!searchBtn) return;

  const make = document.getElementById("vehicleMakeSelect")?.value;
  const model = document.getElementById("vehicleModelSelect")?.value;
  const year = document.getElementById("vehicleYearSelect")?.value;
  const category = document.getElementById("partCategorySelect")?.value;

  searchBtn.disabled = !(make && model && year && (selectedGuidedPart || category));
}

function buildGuidedPartsConversationContext(make, model, year, category, partLabel) {
  const catalog = PROPERTY_CONFIG?.auto_parts?.catalog || [];
  const selectedPart = catalog.find((item) => item.name === partLabel) || {};
  const effectiveCategory = selectedPart.category || category || partLabel;
  const offers = (PROPERTY_CONFIG?.auto_parts?.offers || []).filter((offer) => {
    if (!offer.active) return false;
    if (!effectiveCategory) return true;
    return (offer.categories || []).includes(effectiveCategory);
  });

  return {
    type: "auto_parts_search",
    vehicle: { make, model, year },
    part: {
      name: selectedPart.name || (partLabel === "otro repuesto" ? "" : partLabel),
      category: effectiveCategory,
      sku: selectedPart.sku || "",
      related_parts: selectedPart.related_parts || []
    },
    offers
  };
}

function submitGuidedPartsSearch() {
  const input = document.getElementById("questionInput");
  const make = document.getElementById("vehicleMakeSelect")?.value;
  const model = document.getElementById("vehicleModelSelect")?.value;
  const year = document.getElementById("vehicleYearSelect")?.value;
  const category = document.getElementById("partCategorySelect")?.value;
  const part = selectedGuidedPart || category;

  if (!input || !make || !model || !year || !part) return;

  activeConversationContext = buildGuidedPartsConversationContext(
    make,
    model,
    year,
    category,
    part
  );

  input.value = CURRENT_LANG.startsWith("en")
    ? `${make} ${model} ${year} ${part}. Check compatibility, active offers and preventive related parts.`
    : `${make} ${model} ${year} ${part}. Revisa compatibilidad, ofertas activas y repuestos preventivos relacionados.`;
  askAI();
}
