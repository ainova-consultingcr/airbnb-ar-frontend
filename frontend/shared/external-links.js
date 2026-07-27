/* Shared, protocol-safe external links and WhatsApp helpers. */
"use strict";

function openExternalUrl(url) {
  if (!url) return;

  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return;
    window.open(parsed.href, "_blank", "noopener,noreferrer");
  } catch (error) {
    console.warn("URL inválida:", url);
  }
}
function openWhatsApp(phone, message) {
  const cleanPhone = String(phone || "").replace(/\D/g, "");
  if (!cleanPhone) return;
  const text = encodeURIComponent(message || "Hola, quiero recibir información.");
  openExternalUrl(`https://wa.me/${cleanPhone}?text=${text}`);
}
