/* AVI Farmasi experience: extracted from the legacy application shell. */
"use strict";

let selectedWellnessSafetyNotes = new Set();

function setupGuidedWellnessSearch() {
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
  if (PROPERTY_CONFIG?.type !== "wellness_sales_assistant") return false;

  const preset = inferWellnessShortcut(text);
  const goalSelect = document.getElementById("wellnessGoalSelect");
  const budgetSelect = document.getElementById("wellnessBudgetSelect");

  if (preset?.goal && goalSelect) goalSelect.value = preset.goal;
  if (preset?.budget && budgetSelect) budgetSelect.value = preset.budget;
  updateGuidedWellnessSearchButton();

  const langKey = CURRENT_LANG.startsWith("en") ? "en" : "es";
  focusGuidedWellnessForm(
    langKey === "en"
      ? "Good. I preselected what I could. Complete the remaining selectors so I can recommend Farmasi products responsibly."
      : "Listo. Preseleccione lo que pude. Completa los demas selectores para recomendar productos Farmasi de forma responsable."
  );
  return true;
}
