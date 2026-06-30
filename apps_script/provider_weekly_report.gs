/**
 * Reporte semanal individual para proveedores de AVI.
 * Requiere weekly_report.gs en el mismo proyecto de Google Apps Script.
 */
const AVI_PROVIDER_CONFIG = {
  providers: {
    tour_catarata: {
      name: "Tour Catarata",
      itemNames: ["Tour Catarata"],
      propertyIds: ["hotel_demo"],
      recipients: ["proveedor@example.com"],
      replyTo: "",
      active: true
    }
  }
};

function sendWeeklyProviderReports() {
  const spreadsheet = getAviSpreadsheet_();
  Object.keys(AVI_PROVIDER_CONFIG.providers).forEach((providerId) => {
    const config = AVI_PROVIDER_CONFIG.providers[providerId];
    if (!config.active || !(config.recipients || []).length) return;

    const report = buildWeeklyProviderReport_(spreadsheet, providerId, config);
    MailApp.sendEmail({
      to: config.recipients.join(","),
      replyTo: config.replyTo || undefined,
      subject: `Tu visibilidad en AVI - ${config.name}`,
      htmlBody: renderWeeklyProviderReport_(report),
      name: "AVI Intelligence"
    });
  });
}

function installWeeklyProviderReportTrigger() {
  removeWeeklyProviderReportTriggers();
  ScriptApp.newTrigger("sendWeeklyProviderReports")
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.MONDAY)
    .atHour(8)
    .create();
}

function removeWeeklyProviderReportTriggers() {
  ScriptApp.getProjectTriggers().forEach((trigger) => {
    if (trigger.getHandlerFunction() === "sendWeeklyProviderReports") {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

function sendTestProviderReports() {
  sendWeeklyProviderReports();
}

function buildWeeklyProviderReport_(spreadsheet, providerId, config) {
  const now = new Date();
  const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const validNames = (config.itemNames || [config.name]).map(providerKey_);
  const validProperties = (config.propertyIds || []).map(providerKey_);
  const allowedEvents = [
    "provider_impression", "info_click", "whatsapp_click",
    "reservation_started", "reservation_sent"
  ];

  const events = readSheetObjects_(spreadsheet, AVI_CONFIG.sheets.events)
    .filter((row) => {
      const timestamp = asDate_(row.timestamp);
      const propertyMatches = !validProperties.length || validProperties.includes(providerKey_(row.property));
      return timestamp >= start && timestamp <= now &&
        propertyMatches && validNames.includes(providerKey_(row.item_name)) &&
        allowedEvents.includes(providerKey_(row.event_type));
    });

  const count = (types) => events.filter((row) => types.includes(providerKey_(row.event_type))).length;
  const impressions = count(["provider_impression"]);
  const infoClicks = count(["info_click"]);
  const whatsappClicks = count(["whatsapp_click", "reservation_started", "reservation_sent"]);
  const sessions = {};
  events.forEach((row) => {
    const sessionId = providerMetadata_(row.metadata).session_id;
    if (sessionId) sessions[String(sessionId)] = true;
  });

  const propertyMap = {};
  events.forEach((row) => {
    const name = String(row.property || "AVI");
    propertyMap[name] = propertyMap[name] || { name, impressions: 0, infoClicks: 0, whatsappClicks: 0 };
    const type = providerKey_(row.event_type);
    if (type === "provider_impression") propertyMap[name].impressions++;
    if (type === "info_click") propertyMap[name].infoClicks++;
    if (["whatsapp_click", "reservation_started", "reservation_sent"].includes(type)) {
      propertyMap[name].whatsappClicks++;
    }
  });

  return {
    providerId,
    providerName: config.name,
    periodStart: formatDate_(start),
    periodEnd: formatDate_(now),
    impressions,
    infoClicks,
    whatsappClicks,
    uniquePeople: Object.keys(sessions).length,
    engagementRate: impressions ? Math.min(100, Math.round(((infoClicks + whatsappClicks) / impressions) * 1000) / 10) : 0,
    properties: Object.keys(propertyMap).map((key) => propertyMap[key])
  };
}

function renderWeeklyProviderReport_(report) {
  const propertyRows = report.properties.length
    ? report.properties.map((row) => `
      <tr>
        <td style="padding:11px 8px;border-bottom:1px solid #dfe7ef"><b>${escapeHtml_(row.name)}</b></td>
        <td style="padding:11px 8px;border-bottom:1px solid #dfe7ef">${row.impressions}</td>
        <td style="padding:11px 8px;border-bottom:1px solid #dfe7ef">${row.infoClicks}</td>
        <td style="padding:11px 8px;border-bottom:1px solid #dfe7ef">${row.whatsappClicks}</td>
      </tr>`).join("")
    : '<tr><td colspan="4" style="padding:18px;color:#65748b">Todav\u00eda no hay interacciones en este periodo.</td></tr>';

  return `
  <div style="margin:0;padding:24px;background:#f5f8f7;color:#102034;font-family:Arial,sans-serif">
    <div style="max-width:880px;margin:auto">
      <div style="padding:30px;border-radius:24px;color:#fff;background:linear-gradient(125deg,#0d3f38,#23846d)">
        <div style="font-size:12px;letter-spacing:2px;color:#b8e986;font-weight:bold">AVI \u00b7 EVIDENCIA DE VISIBILIDAD</div>
        <h1 style="margin:10px 0;font-size:38px;line-height:1.05">${escapeHtml_(report.providerName)} s\u00ed est\u00e1 siendo visto</h1>
        <p style="margin:0;color:#dcefe9">Resultados exclusivos de tu negocio en AVI \u00b7 ${escapeHtml_(report.periodStart)} - ${escapeHtml_(report.periodEnd)}</p>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:10px;margin:16px 0">
        ${providerMetric_("Personas interesadas", report.uniquePeople)}
        ${providerMetric_("Veces mostrado", report.impressions)}
        ${providerMetric_("Clics en informaci\u00f3n", report.infoClicks)}
        ${providerMetric_("Clics a WhatsApp", report.whatsappClicks)}
        ${providerMetric_("Interacci\u00f3n", report.engagementRate + "%")}
      </div>
      <div style="padding:22px;background:#fff;border:1px solid #dfe7ef;border-radius:18px">
        <h2 style="margin:0 0 14px">Tu rendimiento por alojamiento</h2>
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <tr><th style="text-align:left;padding:8px">Hotel o Airbnb</th><th style="text-align:left;padding:8px">Visto</th><th style="text-align:left;padding:8px">Info</th><th style="text-align:left;padding:8px">WhatsApp</th></tr>
          ${propertyRows}
        </table>
      </div>
      <p style="color:#65748b;font-size:12px;text-align:center">Este correo contiene \u00fanicamente m\u00e9tricas de ${escapeHtml_(report.providerName)}.</p>
    </div>
  </div>`;
}

function providerMetric_(label, value) {
  return `<div style="min-width:145px;flex:1;padding:16px;background:#fff;border:1px solid #dfe7ef;border-radius:16px"><span style="color:#65748b;font-size:12px">${escapeHtml_(label)}</span><b style="display:block;margin-top:6px;font-size:26px">${escapeHtml_(value)}</b></div>`;
}

function providerMetadata_(value) {
  if (value && typeof value === "object") return value;
  try { return JSON.parse(value || "{}"); } catch (error) { return {}; }
}

function providerKey_(value) {
  return String(value || "").trim().toLowerCase();
}
