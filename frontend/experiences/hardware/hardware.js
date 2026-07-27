/* AVI Hardware experience: extracted from the shared application shell. */
"use strict";

function setupGuidedHardwareSearch() {
  const wrapper = document.getElementById("guidedHardwareSearch");
  if (!wrapper) return;

  if (PROPERTY_CONFIG?.type !== "hardware_store" || !PROPERTY_CONFIG?.hardware) {
    wrapper.classList.remove("visible");
    return;
  }

  wrapper.classList.add("visible");

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const title = wrapper.querySelector(".guided-title");
  const projectSelect = document.getElementById("hardwareProjectSelect");
  const categorySelect = document.getElementById("hardwareCategorySelect");
  const searchBtn = document.getElementById("guidedHardwareSearchBtn");
  const projects = getHardwareProjects();
  const categories = getHardwareCategories();

  title.textContent = langKey === "en"
    ? "Find products by project"
    : "Encuentra lo que necesitas por proyecto";
  searchBtn.textContent = langKey === "en" ? "Ask AVI" : "Consultar con AVI";

  fillSelect(projectSelect, [
    { value: "", label: langKey === "en" ? "Project" : "Proyecto" },
    ...projects.map((project) => ({ value: project, label: project }))
  ]);

  fillSelect(categorySelect, [
    { value: "", label: langKey === "en" ? "Category" : "Categoria" },
    ...categories.map((category) => ({ value: category, label: getHardwareCategoryLabel(category, langKey) }))
  ]);

  renderGuidedHardwareChips();
  updateGuidedHardwareSearchButton();

  projectSelect.onchange = () => {
    renderGuidedHardwareChips();
    updateGuidedHardwareSearchButton();
  };
  categorySelect.onchange = () => {
    renderGuidedHardwareChips();
    updateGuidedHardwareSearchButton();
  };
  searchBtn.onclick = submitGuidedHardwareSearch;
}

function getHardwareProjects() {
  const projectSet = new Set();
  (PROPERTY_CONFIG?.hardware?.store_sections || []).forEach((section) => {
    (section.projects || []).forEach((project) => projectSet.add(project));
  });
  (PROPERTY_CONFIG?.hardware?.catalog || []).forEach((item) => {
    (item.projects || []).forEach((project) => projectSet.add(project));
  });
  return Array.from(projectSet);
}

function getHardwareCategories() {
  const categorySet = new Set();
  (PROPERTY_CONFIG?.hardware?.store_sections || []).forEach((section) => {
    if (section.id) categorySet.add(section.id);
  });
  (PROPERTY_CONFIG?.hardware?.catalog || []).forEach((item) => {
    if (item.category) categorySet.add(item.category);
  });
  return Array.from(categorySet);
}

function getHardwareCategoryLabel(category, langKey) {
  const section = (PROPERTY_CONFIG?.hardware?.store_sections || []).find((item) => item.id === category);
  return localizedValue(section?.name, category);
}

function getCompatibleHardwareItems() {
  const project = document.getElementById("hardwareProjectSelect")?.value;
  const category = document.getElementById("hardwareCategorySelect")?.value;
  const catalog = PROPERTY_CONFIG?.hardware?.catalog || [];

  return catalog.filter((item) => {
    const matchesCategory = !category || item.category === category;
    const matchesProject = !project || (item.projects || []).includes(project);
    return matchesCategory && matchesProject;
  });
}

function renderGuidedHardwareChips() {
  const container = document.getElementById("guidedHardwareChips");
  if (!container) return;

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const project = document.getElementById("hardwareProjectSelect")?.value;
  const category = document.getElementById("hardwareCategorySelect")?.value;
  const items = getCompatibleHardwareItems();
  container.innerHTML = "";

  if (!project && !category) {
    const guide = document.createElement("button");
    guide.className = "part-chip";
    guide.disabled = true;
    guide.textContent = langKey === "en"
      ? "Choose a project or category first"
      : "Elige un proyecto o categoria primero";
    container.appendChild(guide);
    return;
  }

  if (!items.length) {
    const empty = document.createElement("button");
    empty.className = "part-chip";
    empty.disabled = true;
    empty.textContent = langKey === "en" ? "No matching item in catalog" : "Sin coincidencias en catalogo";
    container.appendChild(empty);
  }

  items.forEach((item) => {
    const chip = document.createElement("button");
    chip.className = "part-chip";
    chip.textContent = item.aisle ? `${item.name} - ${item.aisle}` : item.name;
    chip.onclick = () => submitGuidedHardwareSearch(item);
    container.appendChild(chip);
  });

  const otherChip = document.createElement("button");
  otherChip.className = "part-chip";
  otherChip.textContent = langKey === "en" ? "I need something else" : "No veo lo que busco";
  otherChip.onclick = () => submitGuidedHardwareSearch(null);
  container.appendChild(otherChip);
}

function updateGuidedHardwareSearchButton() {
  const searchBtn = document.getElementById("guidedHardwareSearchBtn");
  if (!searchBtn) return;

  const project = document.getElementById("hardwareProjectSelect")?.value;
  const category = document.getElementById("hardwareCategorySelect")?.value;
  searchBtn.disabled = !(project || category);
}

function buildHardwareConversationContext(project, category, item) {
  const section = (PROPERTY_CONFIG?.hardware?.store_sections || []).find((entry) => entry.id === category);
  const offers = (PROPERTY_CONFIG?.hardware?.offers || []).filter((offer) => {
    if (!offer.active) return false;
    return !category || (offer.categories || []).includes(category);
  });
  const workshops = (PROPERTY_CONFIG?.hardware?.workshops || []).filter((workshop) => {
    return !category || workshop.category === category;
  });

  return {
    type: "hardware_search",
    action_type: "hardware_search",
    topic: category ? getHardwareCategoryLabel(category, CURRENT_LANG.startsWith("en") ? "en" : "es") : "ferreteria",
    item: item || {
      name: project || getHardwareCategoryLabel(category, CURRENT_LANG.startsWith("en") ? "en" : "es"),
      category,
      aisle: section?.aisle || ""
    },
    options: [
      ...(item ? [item] : getCompatibleHardwareItems()),
      ...offers,
      ...workshops
    ].slice(0, 5)
  };
}

function submitGuidedHardwareSearch(selectedItem = null) {
  const input = document.getElementById("questionInput");
  const project = document.getElementById("hardwareProjectSelect")?.value;
  const category = document.getElementById("hardwareCategorySelect")?.value;
  const categoryLabel = category
    ? getHardwareCategoryLabel(category, CURRENT_LANG.startsWith("en") ? "en" : "es")
    : "";

  if (!input || (!project && !category && !selectedItem)) return;

  activeConversationContext = buildHardwareConversationContext(project, category, selectedItem);
  const productText = selectedItem
    ? `${selectedItem.name}${selectedItem.aisle ? ` en ${selectedItem.aisle}` : ""}`
    : categoryLabel || project;

  input.value = CURRENT_LANG.startsWith("en")
    ? `${project ? `Project: ${project}. ` : ""}I need help with ${productText}. Show aisle, offers, workshops and useful add-ons.`
    : `${project ? `Proyecto: ${project}. ` : ""}Necesito ayuda con ${productText}. Muestra pasillo, ofertas, charlas y complementos utiles.`;
  askAI();
}
