// Shared helpers for guided forms.
function fillSelect(select, options) {
  if (!select) return;

  select.innerHTML = "";
  options.forEach((option) => {
    const element = document.createElement("option");
    element.value = option.value;
    element.textContent = option.label;
    select.appendChild(element);
  });
}
