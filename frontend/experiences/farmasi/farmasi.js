/* AVI Farmasi experience: extracted from the legacy application shell. */
"use strict";

let selectedWellnessSafetyNotes = new Set();

function setupGuidedWellnessSearch() {
  if (PROPERTY_CONFIG?.type === "wellness_sales_assistant") setupFarmasiCommerce();
  const wrapper = document.getElementById("guidedWellnessSearch");
  if (!wrapper) return;

  if (PROPERTY_CONFIG?.type !== "wellness_sales_assistant") {
    wrapper.classList.remove("visible");
    return;
  }

  wrapper.classList.add("visible");
  selectedWellnessSafetyNotes = new Set();

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const title = wrapper.querySelector(".guided-title");
  const goalSelect = document.getElementById("wellnessGoalSelect");
  const ageSelect = document.getElementById("wellnessAgeSelect");
  const weightSelect = document.getElementById("wellnessWeightSelect");
  const targetSelect = document.getElementById("wellnessTargetSelect");
  const activitySelect = document.getElementById("wellnessActivitySelect");
  const dietSelect = document.getElementById("wellnessDietSelect");
  const exerciseSelect = document.getElementById("wellnessExerciseSelect");
  const budgetSelect = document.getElementById("wellnessBudgetSelect");
  const searchBtn = document.getElementById("guidedWellnessSearchBtn");

  title.textContent = langKey === "en"
    ? "Choose your Farmasi profile"
    : "Selecciona tu perfil Farmasi";
  searchBtn.textContent = langKey === "en" ? "Get recommendation" : "Recomendar con AVI";

  fillSelect(goalSelect, [
    { value: "", label: langKey === "en" ? "Main goal" : "Objetivo principal" },
    { value: "weight_support", label: langKey === "en" ? "Weight support" : "Bajar o controlar peso" },
    { value: "energy", label: langKey === "en" ? "More energy" : "Mas energia" },
    { value: "workout_support", label: langKey === "en" ? "Workout support" : "Apoyo para entrenar" },
    { value: "skin_hair_nails", label: langKey === "en" ? "Skin, hair and nails" : "Piel, cabello y unas" },
    { value: "wellness", label: langKey === "en" ? "General wellness" : "Bienestar general" }
  ]);

  fillSelect(ageSelect, [
    { value: "", label: langKey === "en" ? "Age range" : "Rango de edad" },
    { value: "under_18", label: langKey === "en" ? "Under 18" : "Menor de 18" },
    { value: "18_24", label: "18-24" },
    { value: "25_34", label: "25-34" },
    { value: "35_44", label: "35-44" },
    { value: "45_54", label: "45-54" },
    { value: "55_plus", label: "55+" }
  ]);

  fillSelect(weightSelect, [
    { value: "", label: langKey === "en" ? "Current weight" : "Peso actual aproximado" },
    { value: "under_120_lb", label: langKey === "en" ? "Under 120 lb" : "Menos de 120 lb" },
    { value: "120_150_lb", label: "120-150 lb" },
    { value: "151_180_lb", label: "151-180 lb" },
    { value: "181_220_lb", label: "181-220 lb" },
    { value: "over_220_lb", label: langKey === "en" ? "Over 220 lb" : "Mas de 220 lb" },
    { value: "prefer_not_say", label: langKey === "en" ? "Prefer not to say" : "Prefiero no indicar" }
  ]);

  fillSelect(targetSelect, [
    { value: "", label: langKey === "en" ? "Goal / target" : "Meta principal" },
    { value: "lose_5_10_lb", label: langKey === "en" ? "Lose 5-10 lb" : "Bajar 5-10 lb" },
    { value: "lose_10_20_lb", label: langKey === "en" ? "Lose 10-20 lb" : "Bajar 10-20 lb" },
    { value: "maintain_weight", label: langKey === "en" ? "Maintain weight" : "Mantener peso" },
    { value: "more_energy", label: langKey === "en" ? "More energy" : "Tener mas energia" },
    { value: "tone_or_strength", label: langKey === "en" ? "Tone/strength" : "Tonificar o fuerza" },
    { value: "skin_hair_nails", label: langKey === "en" ? "Skin/hair/nails" : "Piel/cabello/unas" }
  ]);

  fillSelect(activitySelect, [
    { value: "", label: langKey === "en" ? "Activity level" : "Nivel de actividad" },
    { value: "sedentary", label: langKey === "en" ? "Sedentary" : "Sedentario" },
    { value: "light", label: langKey === "en" ? "Light activity" : "Actividad ligera" },
    { value: "moderate", label: langKey === "en" ? "Moderate activity" : "Actividad moderada" },
    { value: "active", label: langKey === "en" ? "Active" : "Activo" }
  ]);

  fillSelect(dietSelect, [
    { value: "", label: langKey === "en" ? "Diet style" : "Tipo de alimentacion" },
    { value: "no_plan", label: langKey === "en" ? "No specific plan" : "Sin plan especifico" },
    { value: "balanced", label: langKey === "en" ? "Balanced" : "Balanceada" },
    { value: "high_protein", label: langKey === "en" ? "High protein" : "Alta en proteina" },
    { value: "low_carb", label: langKey === "en" ? "Low carb" : "Baja en carbohidratos" },
    { value: "vegetarian", label: langKey === "en" ? "Vegetarian" : "Vegetariana" }
  ]);

  fillSelect(exerciseSelect, [
    { value: "", label: langKey === "en" ? "Willing to exercise?" : "Dispuesto a ejercitarse?" },
    { value: "yes", label: langKey === "en" ? "Yes" : "Si" },
    { value: "some", label: langKey === "en" ? "A little" : "Un poco" },
    { value: "no", label: "No" }
  ]);

  fillSelect(budgetSelect, [
    { value: "", label: langKey === "en" ? "Monthly budget" : "Presupuesto mensual" },
    { value: "under_35", label: langKey === "en" ? "Under $35" : "Menos de $35" },
    { value: "35_60", label: "$35-$60" },
    { value: "60_100", label: "$60-$100" },
    { value: "100_plus", label: "$100+" }
  ]);

  [goalSelect, ageSelect, weightSelect, targetSelect, activitySelect, dietSelect, exerciseSelect, budgetSelect]
    .filter(Boolean)
    .forEach((field) => {
      field.onchange = updateGuidedWellnessSearchButton;
      field.oninput = updateGuidedWellnessSearchButton;
    });

  renderGuidedWellnessChips();
  updateGuidedWellnessSearchButton();
  searchBtn.onclick = submitGuidedWellnessSearch;
}

const FARMASI_SELLER_SLUG = new URLSearchParams(window.location.search).get("seller") || "ana";
let FARMASI_SELLER = { id: "", slug: FARMASI_SELLER_SLUG, display_name: "Asesora Farmasi", whatsapp: "" };
const FARMASI_CUSTOMER_SESSION = localStorage.getItem("avi_farmasi_customer_session")
  || (crypto.randomUUID?.() || `customer-${Date.now()}-${Math.random().toString(16).slice(2)}`);
localStorage.setItem("avi_farmasi_customer_session", FARMASI_CUSTOMER_SESSION);
let farmasiCart = JSON.parse(localStorage.getItem("avi_farmasi_cart") || "{}");
let farmasiSellerToken = sessionStorage.getItem(`avi_farmasi_seller_token_${FARMASI_SELLER_SLUG}`) || "";

function farmasiMoney(value) { return `$${Number(value || 0).toFixed(2)}`; }
function saveFarmasiCart() {
  renderFarmasiCart();
  try {
    localStorage.setItem("avi_farmasi_cart", JSON.stringify(farmasiCart));
  } catch (error) {
    console.warn("No se pudo guardar el carrito Farmasi localmente:", error);
  }
}

function setupFarmasiCommerce() {
  loadFarmasiSeller();
  if (new URLSearchParams(window.location.search).get("view") === "seller") {
    setupFarmasiSellerView();
    return;
  }
  renderFarmasiCart();
  const productsRoot = document.getElementById("farmasiProducts");
  if (productsRoot && !productsRoot.dataset.cartHandlerReady) {
    productsRoot.dataset.cartHandlerReady = "true";
    productsRoot.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-farmasi-add]");
      if (button) addFarmasiToCart(button.dataset.farmasiAdd, button);
    });
  }
}

async function loadFarmasiSeller() {
  const response = await fetch(`${API_BASE_URL}/farmasi/sellers/${encodeURIComponent(FARMASI_SELLER_SLUG)}`);
  if (!response.ok) {
    showARAnswer("El enlace de esta asesora no es válido o ya no está activo.", false);
    return false;
  }
  FARMASI_SELLER = await response.json();
  const propertyName = document.getElementById("propertyName");
  if (propertyName) propertyName.textContent = FARMASI_SELLER.display_name;
  return true;
}

function setupFarmasiSellerView() {
  document.body.classList.add("farmasi-seller-mode");
  document.getElementById("responseCard")?.classList.remove("visible");
  ["suggestions", "actionArea", "ui"].forEach(id => {
    const element = document.getElementById(id);
    if (element) element.hidden = true;
  });
  const sellerView = document.getElementById("farmasiSellerView");
  if (!sellerView) return;
  document.body.appendChild(sellerView);
  sellerView.hidden = false;
  document.getElementById("farmasiSellerLoginForm").onsubmit = loginFarmasiSeller;
  document.getElementById("farmasiSellerLogout").onclick = logoutFarmasiSeller;
  showFarmasiSellerSession(Boolean(farmasiSellerToken));
  if (farmasiSellerToken) loadFarmasiOrders();
}

function showFarmasiSellerSession(authenticated) {
  const login = document.getElementById("farmasiSellerLogin");
  const dashboard = document.getElementById("farmasiSellerDashboard");
  if (login) login.hidden = authenticated;
  if (dashboard) dashboard.hidden = !authenticated;
}

async function loginFarmasiSeller(event) {
  event.preventDefault();
  if (!FARMASI_SELLER.id && !(await loadFarmasiSeller())) return;
  const error = document.getElementById("farmasiSellerLoginError");
  error.textContent = "";
  const response = await fetch(`${API_BASE_URL}/farmasi/seller/login`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      seller_slug: FARMASI_SELLER_SLUG,
      username: document.getElementById("farmasiSellerUser").value,
      password: document.getElementById("farmasiSellerPassword").value
    })
  });
  if (!response.ok) {
    error.textContent = "Usuario o contraseña incorrectos.";
    return;
  }
  const session = await response.json();
  farmasiSellerToken = session.access_token;
  sessionStorage.setItem(`avi_farmasi_seller_token_${FARMASI_SELLER_SLUG}`, farmasiSellerToken);
  showFarmasiSellerSession(true);
  loadFarmasiOrders();
}

async function logoutFarmasiSeller() {
  if (farmasiSellerToken) {
    await fetch(`${API_BASE_URL}/farmasi/seller/logout`, {
      method: "POST",
      headers: {Authorization: `Bearer ${farmasiSellerToken}`}
    });
  }
  farmasiSellerToken = "";
  sessionStorage.removeItem(`avi_farmasi_seller_token_${FARMASI_SELLER_SLUG}`);
  showFarmasiSellerSession(false);
}

function showFarmasiRecommendations(question = "") {
  const store = document.getElementById("farmasiStore");
  if (!store) return;
  const responseBody = document.querySelector("#responseCard .response-body");
  if (responseBody && store.parentElement !== responseBody) {
    responseBody.appendChild(store);
  }
  responseBody?.classList.add("farmasi-results-visible");
  const preset = inferWellnessShortcut(question);
  const catalog = PROPERTY_CONFIG?.wellness?.catalog || [];
  const products = preset?.goal ? getFarmasiRelevantProducts(preset.goal) : catalog;
  renderFarmasiProducts(products);
  store.hidden = false;
}

function addFarmasiToCart(sku, button) {
  const product = (PROPERTY_CONFIG?.wellness?.catalog || [])
    .find(item => String(item.sku) === String(sku));
  if (!product) return;
  if (!farmasiCart || typeof farmasiCart !== "object" || Array.isArray(farmasiCart)) farmasiCart = {};
  farmasiCart[product.sku] = {
    sku: product.sku,
    name: product.name,
    price: product.demo_price,
    quantity: (farmasiCart[product.sku]?.quantity || 0) + 1
  };
  if (button) button.textContent = "Agregado ✓";
  saveFarmasiCart();
}

function renderFarmasiProducts(products) {
  const root = document.getElementById("farmasiProducts");
  if (!root) return;
  root.innerHTML = products.filter(p => p.availability === "in_stock").slice(0, 6).map(p => `
    <article class="farmasi-product">
      <img src="${p.image_url}" alt="${p.name}">
      <h4>${p.name}</h4><div class="farmasi-price">${farmasiMoney(p.demo_price)}</div>
      <button type="button" data-farmasi-add="${p.sku}">Agregar</button>
    </article>`).join("");
}

function renderFarmasiCart() {
  const root = document.getElementById("farmasiCart");
  if (!root) return;
  const items = Object.values(farmasiCart);
  const badge = document.getElementById("farmasiCartBadge");
  const count = items.reduce((sum, item) => sum + item.quantity, 0);
  if (badge) badge.textContent = `${count} producto${count === 1 ? "" : "s"}`;
  if (!items.length) { root.innerHTML = '<div class="farmasi-demo-note">Tu carrito temporal está vacío.</div>'; return; }
  const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
  root.innerHTML = `<div class="farmasi-cart-head"><strong>Carrito temporal</strong><button id="farmasiClearCart">Vaciar</button></div>
    ${items.map(item => `<div class="farmasi-cart-row"><span>${item.name}</span><span>x${item.quantity}</span><button data-farmasi-remove="${item.sku}">−</button></div>`).join("")}
    <div class="farmasi-cart-total">Total estimado: ${farmasiMoney(total)}</div>
    <button id="farmasiCheckout" class="farmasi-checkout">Solicitar pedido por WhatsApp</button>
    <div class="farmasi-demo-note">La solicitud no es una venta confirmada. La asesora verificará disponibilidad y total final.</div>`;
  root.querySelectorAll("[data-farmasi-remove]").forEach(button => button.onclick = () => {
    const item = farmasiCart[button.dataset.farmasiRemove];
    if (--item.quantity <= 0) delete farmasiCart[button.dataset.farmasiRemove];
    saveFarmasiCart();
  });
  document.getElementById("farmasiClearCart").onclick = () => { farmasiCart = {}; saveFarmasiCart(); };
  document.getElementById("farmasiCheckout").onclick = requestFarmasiOrder;
}

async function requestFarmasiOrder() {
  const items = Object.values(farmasiCart);
  if (!items.length) return;
  const whatsappWindow = window.open("", "_blank");
  try {
    if (!FARMASI_SELLER.id && !(await loadFarmasiSeller())) throw new Error("seller_not_found");
    const response = await fetch(`${API_BASE_URL}/farmasi/order-requests`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ property_id: CURRENT_PROPERTY, seller_id: FARMASI_SELLER.id, customer_session_id: FARMASI_CUSTOMER_SESSION, items }) });
    if (!response.ok) throw new Error("request_failed");
    const order = await response.json();
    const lines = items.map(item => `• ${item.quantity} x ${item.name}`).join("\n");
    const text = `Hola ${FARMASI_SELLER.display_name}, deseo solicitar este pedido:\n${lines}\nTotal estimado: ${farmasiMoney(order.estimated_total)}\nCódigo: ${order.code}\n\nEntiendo que está pendiente de confirmación.`;
    const whatsappUrl = `https://wa.me/${FARMASI_SELLER.whatsapp}?text=${encodeURIComponent(text)}`;
    if (whatsappWindow) {
      whatsappWindow.opener = null;
      whatsappWindow.location.href = whatsappUrl;
    } else {
      window.location.href = whatsappUrl;
    }
    farmasiCart = {}; saveFarmasiCart();
    showARAnswer(`Solicitud ${order.code} creada. Se abrió WhatsApp para continuar con la asesora.`, false);
  } catch (_) {
    whatsappWindow?.close();
    showARAnswer("No fue posible crear la solicitud. Intenta nuevamente.", false);
  }
}

async function loadFarmasiOrders() {
  const panel = document.getElementById("farmasiSellerPanel");
  const response = await fetch(`${API_BASE_URL}/farmasi/order-requests?property_id=${encodeURIComponent(CURRENT_PROPERTY)}&seller_id=${FARMASI_SELLER.id}`, {
    headers: {Authorization: `Bearer ${farmasiSellerToken}`}
  });
  if (response.status === 401) {
    farmasiSellerToken = "";
    sessionStorage.removeItem(`avi_farmasi_seller_token_${FARMASI_SELLER_SLUG}`);
    showFarmasiSellerSession(false);
    return;
  }
  const orders = response.ok ? await response.json() : [];
  panel.innerHTML = `<strong>Solicitudes recientes</strong>${orders.length ? orders.map(order => `<article class="farmasi-order"><strong>${order.code}</strong><small>${order.items.length} productos · ${farmasiMoney(order.estimated_total)} · ${order.status}</small><div class="farmasi-order-actions"><button data-order="${order.id}" data-status="confirmed">Confirmar</button><button data-order="${order.id}" data-status="cancelled">Cancelar</button></div></article>`).join("") : '<div class="farmasi-demo-note">Aún no hay solicitudes en esta sesión del servidor.</div>'}`;
  panel.querySelectorAll("[data-order]").forEach(button => button.onclick = async () => {
    await fetch(`${API_BASE_URL}/farmasi/order-requests/${button.dataset.order}`, { method:"PATCH", headers:{"Content-Type":"application/json", Authorization:`Bearer ${farmasiSellerToken}`}, body:JSON.stringify({status:button.dataset.status}) });
    loadFarmasiOrders();
  });
}

function renderGuidedWellnessChips() {
  const container = document.getElementById("guidedWellnessChips");
  if (!container) return;

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const chips = [
    { value: "no_known_conditions", label: langKey === "en" ? "No known conditions" : "Sin condiciones conocidas" },
    { value: "medications", label: langKey === "en" ? "Takes medication" : "Toma medicamentos" },
    { value: "pregnancy_breastfeeding", label: langKey === "en" ? "Pregnancy/breastfeeding" : "Embarazo/lactancia" },
    { value: "caffeine_sensitive", label: langKey === "en" ? "Caffeine sensitive" : "Sensible a cafeina" },
    { value: "allergies", label: langKey === "en" ? "Allergies" : "Alergias" }
  ];

  container.innerHTML = "";
  chips.forEach((item) => {
    const chip = document.createElement("button");
    chip.className = "part-chip" + (selectedWellnessSafetyNotes.has(item.value) ? " selected" : "");
    chip.textContent = item.label;
    chip.onclick = () => {
      if (item.value === "no_known_conditions") {
        selectedWellnessSafetyNotes = selectedWellnessSafetyNotes.has(item.value)
          ? new Set()
          : new Set([item.value]);
      } else {
        selectedWellnessSafetyNotes.delete("no_known_conditions");
        if (selectedWellnessSafetyNotes.has(item.value)) {
          selectedWellnessSafetyNotes.delete(item.value);
        } else {
          selectedWellnessSafetyNotes.add(item.value);
        }
      }
      renderGuidedWellnessChips();
      updateGuidedWellnessSearchButton();
    };
    container.appendChild(chip);
  });
}

function updateGuidedWellnessSearchButton() {
  const searchBtn = document.getElementById("guidedWellnessSearchBtn");
  if (!searchBtn) return;

  const goal = document.getElementById("wellnessGoalSelect")?.value;
  const age = document.getElementById("wellnessAgeSelect")?.value;
  const weight = document.getElementById("wellnessWeightSelect")?.value;
  const target = document.getElementById("wellnessTargetSelect")?.value;
  const activity = document.getElementById("wellnessActivitySelect")?.value;
  const diet = document.getElementById("wellnessDietSelect")?.value;
  const exercise = document.getElementById("wellnessExerciseSelect")?.value;
  const budget = document.getElementById("wellnessBudgetSelect")?.value;
  searchBtn.disabled = !(goal && age && weight && target && activity && diet && exercise && budget && selectedWellnessSafetyNotes.size);
}

function getFarmasiRelevantProducts(goal) {
  const catalog = PROPERTY_CONFIG?.wellness?.catalog || [];
  return catalog.filter((item) => {
    const tags = item.goal_tags || [];
    const matchesGoal = !goal || tags.includes(goal) || (goal === "energy" && tags.includes("energy"));
    return matchesGoal;
  }).slice(0, 5);
}

function buildWellnessConversationContext(profile) {
  return {
    type: "wellness_profile",
    action_type: "farmasi_recommendation",
    topic: profile.goal,
    profile,
    options: getFarmasiRelevantProducts(profile.goal)
  };
}

function submitGuidedWellnessSearch() {
  const input = document.getElementById("questionInput");
  if (!input) return;

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  const profile = {
    goal: document.getElementById("wellnessGoalSelect")?.value || "",
    age_range: document.getElementById("wellnessAgeSelect")?.value || "",
    current_weight: document.getElementById("wellnessWeightSelect")?.value || "",
    target: document.getElementById("wellnessTargetSelect")?.value || "",
    activity_level: document.getElementById("wellnessActivitySelect")?.value || "",
    diet_style: document.getElementById("wellnessDietSelect")?.value || "",
    exercise_willingness: document.getElementById("wellnessExerciseSelect")?.value || "",
    budget: document.getElementById("wellnessBudgetSelect")?.value || "",
    safety_notes: Array.from(selectedWellnessSafetyNotes).join(", ")
  };

  if (!(profile.goal && profile.age_range && profile.current_weight && profile.target && profile.activity_level && profile.diet_style && profile.exercise_willingness && profile.budget && profile.safety_notes)) return;

  activeConversationContext = buildWellnessConversationContext(profile);
  input.value = langKey === "en"
    ? `Farmasi product recommendation profile. Wellness goal: ${profile.goal}. Age range: ${profile.age_range}. Weight range: ${profile.current_weight || "not provided"}. Desired result: ${profile.target || "not provided"}. Movement level: ${profile.activity_level}. Eating style: ${profile.diet_style || "not provided"}. Exercise willingness: ${profile.exercise_willingness || "not provided"}. Monthly budget: ${profile.budget}. Safety notes: ${profile.safety_notes}. Recommend official Farmasi products only, mention availability and simple usage guidance. Do not show prices or product URLs. Do not diagnose.`
    : `Perfil para recomendacion de productos Farmasi. Objetivo de bienestar: ${profile.goal}. Rango de edad: ${profile.age_range}. Rango de peso: ${profile.current_weight || "no indicado"}. Resultado deseado: ${profile.target || "no indicado"}. Nivel de movimiento: ${profile.activity_level}. Estilo de alimentacion: ${profile.diet_style || "no indicado"}. Disposicion para ejercicio: ${profile.exercise_willingness || "no indicado"}. Presupuesto mensual: ${profile.budget}. Notas de seguridad: ${profile.safety_notes}. Recomienda solo productos oficiales Farmasi, menciona disponibilidad y forma de uso simple. No muestres precios ni URLs de productos. No diagnostiques.`;
  askAI();
}

function inferWellnessShortcut(text) {
  const normalized = (text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

  if (normalized.includes("bajar") || normalized.includes("peso") || normalized.includes("weight")) {
    return { goal: "weight_support" };
  }
  if (normalized.includes("energia") || normalized.includes("energy")) {
    return { goal: "energy" };
  }
  if (normalized.includes("entren") || normalized.includes("workout") || normalized.includes("exercise")) {
    return { goal: "workout_support" };
  }
  if (normalized.includes("piel") || normalized.includes("cabello") || normalized.includes("unas") || normalized.includes("skin") || normalized.includes("hair") || normalized.includes("nail")) {
    return { goal: "skin_hair_nails" };
  }
  if (normalized.includes("presupuesto") || normalized.includes("budget")) {
    return { budget: "under_35" };
  }
  return null;
}

function focusGuidedWellnessForm(message = "") {
  const wrapper = document.getElementById("guidedWellnessSearch");
  if (!wrapper) return;

  wrapper.classList.add("guided-highlight");
  setTimeout(() => wrapper.classList.remove("guided-highlight"), 1400);
  wrapper.scrollIntoView?.({ behavior: "smooth", block: "nearest" });

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  showARAnswer(
    message || (
      langKey === "en"
        ? "Use the selectors below. Choose your goal, age, weight range, target, activity, budget and safety notes, then tap Get recommendation."
        : "Usa los selectores de abajo. Elige objetivo, edad, rango de peso, meta, actividad, presupuesto y notas de seguridad; luego toca Recomendar con AVI."
    ),
    false
  );
}

function handleWellnessShortcut(text) {
  return false;
}
