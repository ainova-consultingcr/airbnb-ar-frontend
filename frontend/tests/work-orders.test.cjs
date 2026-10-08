const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "..", "experiences", "auto-parts", "workshop-demo.js"), "utf8");

test("Autopartes usa API persistente y no el estado simulado anterior", () => {
  assert.match(source, /\/service-requests/);
  assert.match(source, /\/advisor\/work-orders/);
  assert.match(source, /\/decision\?token=/);
  assert.doesNotMatch(source, /avi_workshop_demo_v1/);
  assert.doesNotMatch(source, /facturaci[oó]n simulada/i);
});

test("la solicitud exige consentimiento y ofrece seguimiento", () => {
  assert.match(source, /consent_to_contact/);
  assert.match(source, /tracking_token/);
  assert.match(source, /data-decision/);
});

test("WhatsApp es contacto humano configurado y AVI conserva la aprobación", () => {
  assert.match(source, /workshopConfig\?\.whatsapp\?\.enabled/);
  assert.match(source, /openWhatsApp\(phone/);
  assert.match(source, /sobre la solicitud \$\{code\}/);
  assert.match(source, /presupuesto y su aprobación permanecen en AVI/i);
  assert.doesNotMatch(source, /mensaje (?:fue )?enviado/i);
  assert.doesNotMatch(source, /tracking_token.*openWhatsApp/);
});

test("el seguimiento separa la decisión formal de la ayuda por WhatsApp", () => {
  assert.match(source, /class="actions"[^>]*><button class="primary" data-decision="approved"/);
  assert.match(source, /wo-human-contact/);
  assert.match(source, /¿Necesitas ayuda\?/);
  assert.match(source, /Ayuda opcional\. El presupuesto y su aprobación permanecen en AVI\./);
  assert.match(source, /whatsappButton\(saved\.code,true\)/);
});

test("la inspección usa disponibilidad integrada con fallback manual", () => {
  assert.match(source, /\/inspection-slots\?days=7/);
  assert.match(source, /data-inspection-start/);
  assert.match(source, /\/inspection\?token=/);
  assert.match(source, /El taller coordinará contigo el horario/);
  assert.match(source, /Diagnóstico del mecánico/);
  assert.match(source, /staffRole==="mechanic"/);
});
