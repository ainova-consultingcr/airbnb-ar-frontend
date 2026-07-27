// AVI application bootstrap.
const questionInput = document.getElementById("questionInput");
if (questionInput) {
  questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      askAI();
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  await loadPropertyConfig();
  await loadExperience(PROPERTY_CONFIG?.type);
  applyBranding(false);
  applyInputBranding();
  renderSuggestionsFromBackend();
  showSuggestions();
  restoreServiceRequest();
});

